# @file gateway.py
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version, along with the "Special Exception" for use of
# the program along with SSL, set forth below. This program is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details. You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by
# post at Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK
#
# Special Exception
# Metaswitch Networks Ltd  grants you permission to copy, modify,
# propagate, and distribute a work formed by combining OpenSSL with The
# Software, or a work derivative of such a combination, even if such
# copying, modification, propagation, or distribution would otherwise
# violate the terms of the GPL. You must comply with the GPL in all
# respects for all of the code used other than OpenSSL.
# "OpenSSL" means OpenSSL toolkit software distributed by the OpenSSL
# Project and licensed under the OpenSSL Licenses, or a work based on such
# software and licensed under the OpenSSL Licenses.
# "OpenSSL Licenses" means the OpenSSL License and Original SSLeay License
# under which the OpenSSL Project distributes the OpenSSL toolkit software,
# as those licenses appear in the file LICENSE-OPENSSL.


import os
import logging
import traceback
import time

from diameter import stack
from twisted.internet import defer
from twisted.internet.task import LoopingCall

from metaswitch.crest import settings
from metaswitch.crest.api.base import penaltycounter, loadmonitor, digest_latency_accumulator, subscription_latency_accumulator
from metaswitch.crest.api import DeferTimeout
from metaswitch.crest.api.exceptions import HSSNotEnabled, HSSOverloaded, HSSConnectionLost, HSSStillConnecting, UserNotIdentifiable, UserNotAuthorized
from metaswitch.common import utils
from metaswitch.crest.api.homestead.auth_vectors import DigestAuthVector, AKAAuthVector
from metaswitch.crest.api.homestead import authtypes
from metaswitch.crest.api.homestead import resultcodes
from metaswitch.crest.api.homestead.cache.handlers import AUTH_TYPES, ORIGINATING

from base64 import b64encode
from binascii import hexlify

from .io import HSSPeerIO

_log = logging.getLogger("crest.api.homestead.hss")

DICT_NAME = "dictionary.xml"
DICT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), DICT_NAME)

JSON_RC = "result-code"
JSON_SCSCF = "scscf"
JSON_MAN_CAP = "mandatory-capabilities"
JSON_OPT_CAP = "optional-capabilities"

class HSSGateway(object):
    """
    Gateway to real HSS. Abstracts away the underlying details of the Cx
    interface to enable fetching of data in a more HTTP-like fashion
    """
    def __init__(self, backend_callbacks):
        if not settings.HSS_ENABLED:
            raise HSSNotEnabled()

        dstack = stack.Stack(product_name="Clearwater", ip4_address=settings.LOCAL_IP)
        dstack.vendor_id = 19444 # Metaswitch
        dstack.loadDictionary("cx", DICT_PATH)
        dstack.identity = settings.PUBLIC_HOSTNAME
        dstack.realm = settings.HS_HOSTNAME

        app = HSSAppListener(dstack, backend_callbacks)
        self.peer_listener = HSSPeerListener(app,
                                             settings.SIP_DIGEST_REALM,
                                             dstack)
        for vendor in settings.CX_SUPPORTED_VENDORS:
            dstack.addSupportedVendor(vendor)
            dstack.registerAuthApplication(app, vendor, 16777216)
        dstack.registerPeerListener(self.peer_listener)
        dstack.registerPeerIO(HSSPeerIO())
        dstack.clientV4Add(settings.HSS_IP, settings.HSS_PORT)

        # Twisted will run dstack.tick every second
        tick = LoopingCall(dstack.tick)
        tick.start(1)

    def get_digest(self, private_id, public_id):
        self.get_av(private_id, public_id, authtypes.SIP_DIGEST)

    @defer.inlineCallbacks
    def get_av(self, private_id, public_id, authtype, autn=None):
        """Gets the SIP digest from the HSS with a Multimedia-Auth-Request.
        Returns None if the subscriber is not found."""
        _log.debug("Getting auth for priv:%s pub:%s authtype:%s autn:%s" % (private_id, public_id, authtype, autn))
        result = yield self.peer_listener.fetch_multimedia_auth(private_id,
                                                                public_id,
                                                                authtype,
                                                                autn)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_ims_subscription(self, private_id, public_id):
        """Gets the IMS subscription information from the HSS with a
        Server-Assignment_request. Returns None if the subscriber is not found."""
        _log.debug("Getting IMS subscription for priv:%s, pub:%s" %
                   (private_id, public_id))
        result = yield self.peer_listener.fetch_server_assignment(private_id,
                                                                  public_id)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_registration_status(self, private_id, public_id, visited_network, auth_type):
        """Gets the registration status information from the HSS with a
        User-Authorization_request. Returns None if the subscriber is not found."""
        _log.debug("Getting registration status for priv:%s, pub:%s" %
                   (private_id, public_id))
        result = yield self.peer_listener.fetch_user_auth(private_id,
                                                          public_id,
                                                          visited_network,
                                                          auth_type)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_location_information(self, public_id, originating, auth_type):
        """Gets the location information from the HSS with a
        Location-Info_request. Returns None if the subscriber is not found."""
        _log.debug("Getting location information for pub:%s" %
                   (public_id))
        result = yield self.peer_listener.fetch_location_info(public_id,
                                                              originating,
                                                              auth_type)
        defer.returnValue(result)

class HSSAppListener(stack.ApplicationListener):
    """
    The HSSAppListener maintains a list of pending requests outstanding on the
    HSS (stored as deferreds), and listens for responses from the HSS. When a
    response arrives, it correlates it with a pending request and injects the
    response into the pending request
    """
    def __init__(self, stack, backend_callbacks):
        self.backend_callbacks = backend_callbacks
        self._pending_responses = {}
        self.cx = stack.getDictionary("cx")

    def add_pending_response(self, request, deferred):
        key = self.request_hash(request)
        existing_responses = self._pending_responses.setdefault(key, [])
        _log.debug("Adding request %s to pending responses" % hash(key))
        existing_responses.append(deferred)

    def request_hash(self, request):
        # To ensure we can correlate requests with this callback, key off the
        # request in a identifiable way. eTe is the request's end-to-end
        # identifier
        return (request.application_id, request.command_code, request.eTe)

    def onAnswer(self, peer, answer):
        try:
            key = self.request_hash(answer)
            if key in self._pending_responses:
                _log.debug("Executing callbacks for pending requests %s" % hash(key))
                for deferred in self._pending_responses.pop(key):
                    deferred.callback(answer)
        except:
            utils.write_core_file(settings.LOG_FILE_PREFIX,
                                  traceback.format_exc())
            _log.exception("Caught exception while processing DIAMETER response")


    @defer.inlineCallbacks
    def onRequest(self, peer, request):
        try:
            if self.cx.isCommand(request, "Push-Profile"):
                yield self.onPushProfileRequest(peer, request)
            elif self.cx.isCommand(request, "Registration-Termination"):
                yield self.onRegistrationTerminationRequest(peer, request)
            else:
                answer = peer.stack.createAnswer(request, resultcodes.DIAMETER_COMMAND_UNSUPPORTED)
                peer.stack.sendByPeer(peer, answer)
        except:
            # We must catch and handle any exception here, as otherwise it will
            # propagate up to the Diameter stack and kill it.
            utils.write_core_file(settings.LOG_FILE_PREFIX,
                                  traceback.format_exc())
            _log.exception("Caught exception while processing DIAMETER request")

    @defer.inlineCallbacks
    def onPushProfileRequest(self, peer, request):
        # Got a Push-Profile-Request.  This can contain digest information,
        # subscriber profile or both.  First check digest information.
        private_id = self.cx.findFirstAVP(request, "User-Name")
        digest = self.cx.findFirstAVP(request, "SIP-Auth-Data-Item",
                                      "SIP-Digest-Authenticate AVP", "Digest-HA1")
        deferreds = []
        if private_id and digest:
            _log.debug("Received Push-Profile containing Digest-HA1 for user %s" %
                       private_id.getOctetString())
            d = self.backend_callbacks.on_digest_change(private_id.getOctetString(),
                                                        digest.getOctetString())
            deferreds.append(d)
        # Now check user data.
        user_data = self.cx.findFirstAVP(request, "User-Data")
        if user_data:
            _log.debug("Received Push-Profile containing User-Data: %s" %
                       user_data.getOctetString())
            d = self.backend_callbacks.on_ims_subscription_change(user_data.getOctetString())
            deferreds.append(d)
        # Build an answer and send it once all deferreds are complete.
        answer = peer.stack.createAnswer(request)
        answer.addAVP(self.cx.findFirstAVP(request, "Vendor-Specific-Application-Id"))
        result_code = self.cx.getAVP("Result-Code")
        try:
            # We specify fireOnOneErrback here to ensure an exception is thrown if either
            # Deferred fails.
            yield defer.DeferredList(deferreds, fireOnOneErrback=True, consumeErrors=True)
            answer.addAVP(result_code.withInteger32(resultcodes.DIAMETER_SUCCESS))
        except:
            _log.exception("Push-Profile-Request cache update failed")
            answer.addAVP(result_code.withInteger32(resultcodes.DIAMETER_UNABLE_TO_COMPLY))
        answer.addAVP(self.cx.findFirstAVP(request, "Auth-Session-State"))
        peer.stack.sendByPeer(peer, answer)

    @defer.inlineCallbacks
    def onRegistrationTerminationRequest(self, peer, request):
        # Got a Registration-Termination-Request.  This tells us we won't get any
        # further notifications, so we should flush the cache now.
        answer = peer.stack.createAnswer(request)
        answer.addAVP(self.cx.findFirstAVP(request, "Vendor-Specific-Application-Id"))
        # Build a list of private IDs and copy it to the answer.
        private_id = self.cx.findFirstAVP(request, "User-Name").getOctetString()
        private_ids = [private_id]
        answer.addAVP(self.cx.getAVP("Associated-Identities").withOctetString(private_id))
        for avp in self.cx.findAVP(request, "Associated-Identities"):
            private_ids.append(avp.getOctetString())
            answer.addAVP(avp)
        # Now get the public IDs.
        public_ids = [avp.getOctetString() for avp in self.cx.findAVP(request, "Public-Identity")]
        # Expire these private and public IDs.
        result_code = self.cx.getAVP("Result-Code")
        try:
            yield self.backend_callbacks.on_forced_expiry(private_ids, public_ids)
            # TODO: Notify Sprout to force deregistration there?
            answer.addAVP(result_code.withInteger32(resultcodes.DIAMETER_SUCCESS))
        except:
            _log.exception("Registration-Termination-Request cache update failed")
            answer.addAVP(result_code.withInteger32(resultcodes.DIAMETER_UNABLE_TO_COMPLY))
        answer.addAVP(self.cx.findFirstAVP(request, "Auth-Session-State"))
        peer.stack.sendByPeer(peer, answer)


class HSSPeerListener(stack.PeerListener):
    def __init__(self, app, domain, stack):
        self.app = app
        self.realm = domain
        self.server_name = "sip:%s:%d" % (settings.SPROUT_HOSTNAME, settings.SPROUT_PORT)
        self.cx = stack.getDictionary("cx")
        self.peer = None
        self.session_id = int(time.time()) << 32

    def connected(self, peer):
        _log.info("Peer %s connected" % peer.identity)
        self.peer = peer

    def get_diameter_result_code(self, request):
        result_code = self.cx.findFirstAVP(request, "Result-Code")
        if not result_code:
            return None
        return result_code.getInteger32()

    def get_diameter_exp_result_vendor(self, request):
        exp_result = self.cx.findFirstAVP(request, "Experimental-Result")
        if not exp_result:
            return None
        return exp_result.getGroup()[0].getInteger32()

    def get_diameter_exp_result_code(self, request):
        exp_result = self.cx.findFirstAVP(request, "Experimental-Result")
        if not exp_result:
            return None
        return exp_result.getGroup()[1].getInteger32()

    def log_diameter_error(self, msg):
        err_code = self.get_diameter_result_code(msg)
        if err_code:
            _log.info("HSS returned error code %d", err_code)
        else:
            err_code = self.get_diameter_exp_result_code(msg)
            vendor = self.get_diameter_exp_result_vendor(msg)
            if (vendor and err_code):
                _log.info("HSS returned vendor ID %d and error code %d" %
                          (vendor, err_code))
            else:
                _log.info("HSS returned error (code unknown)")

    @DeferTimeout.timeout(loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_multimedia_auth(self, private_id, public_id, authtype, autn):
        if self.peer is None:
            raise HSSStillConnecting()
        if not self.peer.alive:
            raise HSSConnectionLost()
        _log.debug("Sending Multimedia-Auth request for %s/%s/%s/%s" % (private_id, public_id, authtype, autn))

        public_id = str(public_id)
        private_id = str(private_id)
        req = self.cx.getCommandRequest(self.peer.stack, "Multimedia-Auth", True)
        self.session_id += 1
        req.addAVP(self.cx.getAVP('Session-Id').withOctetString("%s;%u;%u" % (settings.PUBLIC_HOSTNAME, self.session_id >> 32, self.session_id & 0xffffffff)))
        req.addAVP(self.cx.getAVP('Auth-Session-State').withInteger32(1))
        req.addAVP(self.cx.getAVP('Destination-Realm').withOctetString(self.peer.realm))
        req.addAVP(self.cx.getAVP('Destination-Host').withOctetString(self.peer.identity))
        req.addAVP(self.cx.getAVP('User-Name').withOctetString(private_id))
        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(public_id))
        req.addAVP(self.cx.getAVP('Server-Name').withOctetString(self.server_name))
        req.addAVP(self.cx.getAVP('SIP-Number-Auth-Items').withInteger32(1))

        auth_avp = self.cx.getAVP('SIP-Auth-Data-Item')
        # Update the request depending on the authentication method
        if authtype == authtypes.AKA:
            auth_avp.addAVP(self.cx.getAVP('SIP-Authentication-Scheme').withOctetString('Digest-AKAv1-MD5'))
            if autn:
                auth_avp.addAVP(self.cx.getAVP('SIP-Authorization').withOctetString(autn))
        elif authtype == authtypes.SIP_DIGEST:
            auth_avp.addAVP(self.cx.getAVP('SIP-Authentication-Scheme').withOctetString('SIP Digest'))
        elif settings.LOWERCASE_UNKNOWN:
            auth_avp.addAVP(self.cx.getAVP('SIP-Authentication-Scheme').withOctetString('unknown'))
        else:
            auth_avp.addAVP(self.cx.getAVP('SIP-Authentication-Scheme').withOctetString('Unknown'))

        req.addAVP(auth_avp)

       # Send off message to HSS
        start_time = time.time()
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d

        # Have response, get the authentication scheme from it
        scheme = self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item", "SIP-Authentication-Scheme")
        # Track how long it took (in usec)
        digest_latency_accumulator.accumulate((time.time() - start_time) * 1000000)

        if scheme:
            if "SIP Digest" in scheme.getOctetString():
                digest = self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                              "SIP-Digest-Authenticate AVP", "Digest-HA1").getOctetString()
                realm = self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                             "SIP-Digest-Authenticate AVP", "Digest-Realm").getOctetString()

                # QoP is optional, so needs special handling
                qop_avp = self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                               "SIP-Digest-Authenticate AVP", "Digest-QoP")
                qop = None
                if qop_avp:
                    qop = qop_avp.getOctetString()

                if authtype == authtypes.UNKNOWN:
                    preferred = True
                else:
                    preferred = False

                auth = DigestAuthVector(digest, realm, qop, preferred)
                defer.returnValue(auth)
            elif "Digest-AKAv1-MD5" in scheme.getOctetString():
                # Integrity key and confidentiality key are "LDQUOT
                # *(HEXDIG) RDQUOT" as per TS 24.229 7.2A.1.2
                ck = hexlify(self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                          "Confidentiality-Key").getOctetString())
                ik = hexlify(self.cx.findFirstAVP(answer,
                                                  "SIP-Auth-Data-Item", "Integrity-Key").getOctetString())
                # The digest on the Authorization header is <"> 32LHEX
                # <"> as per RFC 2617 section 3.2.2
                response = hexlify(self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                                        "SIP-Authorization").getOctetString())
                # The nonce on the WWW-Authenticate header is base64
                # encoded as per RFC 3310 section 3.2.
                challenge = b64encode(self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item",
                                                 "SIP-Authenticate").getOctetString())

                auth = AKAAuthVector(challenge, response, ck, ik)
                defer.returnValue(auth)
            else:
                _log.debug("Invalid authentication scheme: %s" % scheme.getOctetString())
                defer.returnValue(None)
        else:
            self.log_diameter_error(answer)
            # If the error is an Overload response, increment the HSS penalty counter
            if self.get_diameter_result_code(answer) == 3004:
                penaltycounter.incr_hss_penalty_count()
                raise HSSOverloaded()
            else:
                # Translated into a 404 higher up the stack
                defer.returnValue(None)

    @DeferTimeout.timeout(loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_server_assignment(self, private_id, public_id):
        if self.peer is None:
            raise HSSStillConnecting()
        if not self.peer.alive:
            raise HSSConnectionLost()
        # Constants to match the enumerated values in 3GPP TS 29.229 s6.3.15
        REGISTRATION = 1
        UNREGISTERED_USER = 3

        _log.debug("Sending Server-Assignment request for %s/%s" % (private_id, public_id))
        req = self.cx.getCommandRequest(self.peer.stack, "Server-Assignment", True)
        self.session_id += 1
        req.addAVP(self.cx.getAVP('Session-Id').withOctetString("%s;%u;%u" % (settings.PUBLIC_HOSTNAME, self.session_id >> 32, self.session_id & 0xffffffff)))
        req.addAVP(self.cx.getAVP('Auth-Session-State').withInteger32(1))
        req.addAVP(self.cx.getAVP('Destination-Realm').withOctetString(self.peer.realm))
        req.addAVP(self.cx.getAVP('Destination-Host').withOctetString(self.peer.identity))

        if private_id:
            # withOctetString takes a sequence of bytes, not a Unicode
            # string, so call bytes() on private_id and public_id
            req.addAVP(self.cx.getAVP('User-Name').withOctetString(bytes(private_id)))

        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(bytes(public_id)))
        req.addAVP(self.cx.getAVP('Server-Name').withOctetString(self.server_name))
        if private_id:
            req.addAVP(self.cx.getAVP('Server-Assignment-Type').withInteger32(REGISTRATION))
        else:
            req.addAVP(self.cx.getAVP('Server-Assignment-Type').withInteger32(UNREGISTERED_USER))
        req.addAVP(self.cx.getAVP('User-Data-Already-Available').withInteger32(0))
        # Send off message to HSS
        start_time = time.time()
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d

        _log.debug("Received Server-Assignment response for %s:" % private_id)
        user_data = self.cx.findFirstAVP(answer, "User-Data")

        # Track how long it took (in usec)
        subscription_latency_accumulator.accumulate((time.time() - start_time) * 1000000)
        if not user_data:
            self.log_diameter_error(answer)
            # If the error is an Overload response, increment the HSS penalty counter
            if self.get_diameter_result_code(answer) == 3004:
                penaltycounter.incr_hss_penalty_count()
                raise HSSOverloaded()
            else:
                # Translated into a 404 higher up the stack
                defer.returnValue(None)

        defer.returnValue(user_data.getOctetString())

    @DeferTimeout.timeout(loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_user_auth(self, private_id, public_id, visited_network, auth_type):
        if self.peer is None:
            raise HSSStillConnecting()
        if not self.peer.alive:
            raise HSSConnectionLost()

        _log.debug("Sending User-Authorization request for %s/%s" % (private_id, public_id))
        req = self.cx.getCommandRequest(self.peer.stack, "User-Authorization", True)
        self.session_id += 1
        req.addAVP(self.cx.getAVP('Session-Id').withOctetString("%s;%u;%u" % (settings.PUBLIC_HOSTNAME, self.session_id >> 32, self.session_id & 0xffffffff)))
        req.addAVP(self.cx.getAVP('Auth-Session-State').withInteger32(1))
        req.addAVP(self.cx.getAVP('Destination-Realm').withOctetString(self.peer.realm))
        req.addAVP(self.cx.getAVP('Destination-Host').withOctetString(self.peer.identity))

        # withOctetString takes a sequence of bytes, not a Unicode string, so call
        # bytes() on private_id, public_id and visited_network
        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(bytes(public_id)))
        req.addAVP(self.cx.getAVP('Visited-Network-Identifier').withOctetString(bytes(visited_network)))
        req.addAVP(self.cx.getAVP('User-Authorization-Type').withInteger32(auth_type))
        req.addAVP(self.cx.getAVP('User-Name').withOctetString(bytes(private_id)))
        # Send off message to HSS
        start_time = time.time()
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d

        _log.debug("Received User-Authorization response for %s/%s:" % (private_id, public_id))
        # Track how long it took (in usec)
        subscription_latency_accumulator.accumulate((time.time() - start_time) * 1000000)
        result_code = self.get_diameter_result_code(answer)
        exp_result_code = self.get_diameter_exp_result_code(answer)

        if result_code == resultcodes.DIAMETER_SUCCESS or exp_result_code in [resultcodes.DIAMETER_FIRST_REGISTRATION,
                                                                              resultcodes.DIAMETER_SUBSEQUENT_REGISTRATION]:
            registration_status = {}
            registration_status[JSON_RC] = result_code if result_code == resultcodes.DIAMETER_SUCCESS else exp_result_code

            server_name = self.cx.findFirstAVP(answer, "Server-Name")
            if server_name:
                registration_status[JSON_SCSCF] = server_name.getOctetString()
            else:
                server_capabilities = self.cx.findFirstAVP(answer, "Server-Capabilities")
                man_capabilities = []
                opt_capabilities = []
                if server_capabilities:
                    man_capabilities = [avp.getInteger32() for avp in self.cx.findAVP(server_capabilities, "Mandatory-Capability")]
                    opt_capabilities = [avp.getInteger32() for avp in self.cx.findAVP(server_capabilities, "Optional-Capability")]
                registration_status[JSON_MAN_CAP] = man_capabilities
                registration_status[JSON_OPT_CAP] = opt_capabilities
        elif exp_result_code in [resultcodes.DIAMETER_ERROR_USER_UNKNOWN, resultcodes.DIAMETER_ERROR_IDENTITIES_DONT_MATCH]:
            self.log_diameter_error(answer)
            raise UserNotIdentifiable()
        elif exp_result_code == resultcodes.DIAMETER_ERROR_ROAMING_NOT_ALLOWED or result_code == resultcodes.DIAMETER_AUTHORIZATION_REJECTED:
            self.log_diameter_error(answer)
            raise UserNotAuthorized()
        elif result_code == resultcodes.DIAMETER_TOO_BUSY:
            # If the error is an Overload response, increment the HSS penalty counter
            penaltycounter.incr_hss_penalty_count()
            self.log_diameter_error(answer)
            raise HSSOverloaded()
        else:
            # Translated into a 500 higher up the stack
            defer.returnValue(None)

        defer.returnValue(registration_status)

    @DeferTimeout.timeout(loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_location_info(self, public_id, originating, auth_type):
        if self.peer is None:
            raise HSSStillConnecting()
        if not self.peer.alive:
            raise HSSConnectionLost()

        _log.debug("Sending Location-Info request for %s" % (public_id))
        req = self.cx.getCommandRequest(self.peer.stack, "Location-Info", True)
        self.session_id += 1
        req.addAVP(self.cx.getAVP('Session-Id').withOctetString("%s;%u;%u" % (settings.PUBLIC_HOSTNAME, self.session_id >> 32, self.session_id & 0xffffffff)))
        req.addAVP(self.cx.getAVP('Auth-Session-State').withInteger32(1))
        req.addAVP(self.cx.getAVP('Destination-Realm').withOctetString(self.peer.realm))
        req.addAVP(self.cx.getAVP('Destination-Host').withOctetString(self.peer.identity))

        # withOctetString takes a sequence of bytes, not a Unicode string, so call
        # bytes() on public_id
        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(bytes(public_id)))
        if auth_type is not None:
            req.addAVP(self.cx.getAVP('User-Authorization-Type').withInteger32(AUTH_TYPES["CAPAB"]))
        if originating is not None:
            req.addAVP(self.cx.getAVP('Originating-Request').withInteger32(ORIGINATING))
        # Send off message to HSS
        start_time = time.time()
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d

        _log.debug("Received Location-Info response for %s:" % public_id)

        # Track how long it took (in usec)
        subscription_latency_accumulator.accumulate((time.time() - start_time) * 1000000)
        result_code = self.get_diameter_result_code(answer)
        exp_result_code = self.get_diameter_exp_result_code(answer)

        if result_code == resultcodes.DIAMETER_SUCCESS or exp_result_code == resultcodes.DIAMETER_UNREGISTERED_SERVICE:
            location_information = {}
            server_name = self.cx.findFirstAVP(answer, "Server-Name")
            if result_code == resultcodes.DIAMETER_SUCCESS and server_name:
                location_information[JSON_RC] = result_code
                location_information[JSON_SCSCF] = server_name.getOctetString()
            else:
                location_information[JSON_RC] = result_code if result_code == resultcodes.DIAMETER_SUCCESS else exp_result_code
                server_capabilities = self.cx.findFirstAVP(answer, "Server-Capabilities")
                man_capabilities = []
                opt_capabilities = []
                if server_capabilities:
                    man_capabilities = [avp.getInteger32() for avp in self.cx.findAVP(server_capabilities, "Mandatory-Capability")]
                    opt_capabilities = [avp.getInteger32() for avp in self.cx.findAVP(server_capabilities, "Optional-Capability")]
                location_information[JSON_MAN_CAP] = man_capabilities
                location_information[JSON_OPT_CAP] = opt_capabilities
        elif exp_result_code in [resultcodes.DIAMETER_ERROR_USER_UNKNOWN, resultcodes.DIAMETER_ERROR_IDENTITY_NOT_REGISTERED]:
            self.log_diameter_error(answer)
            raise UserNotIdentifiable()
        elif result_code == resultcodes.DIAMETER_TOO_BUSY:
            # If the error is an Overload response, increment the HSS penalty counter
            penaltycounter.incr_hss_penalty_count()
            self.log_diameter_error(answer)
            raise HSSOverloaded()
        else:
            # Translated into a 500 higher up the stack
            defer.returnValue(None)

        defer.returnValue(location_information)

    def disconnected(self, peer):
        _log.debug("Peer %s disconnected" % peer.identity)
        self.peer.alive = False

