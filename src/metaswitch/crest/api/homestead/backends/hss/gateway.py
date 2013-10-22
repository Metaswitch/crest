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

from diameter import stack
from twisted.internet import defer
from twisted.internet.task import LoopingCall

from metaswitch.crest import settings
from metaswitch.crest.api._base import _penaltycounter, _loadmonitor
from metaswitch.crest.api import DeferTimeout
from .io import HSSPeerIO

_log = logging.getLogger("crest.api.homestead.hss")

DICT_NAME = "dictionary.xml"
DICT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), DICT_NAME)

DIAMETER_SUCCESS = 2001
DIAMETER_COMMAND_UNSUPPORTED = 3001
DIAMETER_UNABLE_TO_COMPLY = 5012

# HSS-specific Exceptions
class HSSNotEnabled(Exception):
    """Exception to throw if gateway is created without a valid HSS_IP"""
    pass


class HSSNotFound(Exception):
    """Exception to throw if a request cannot be completed because a resource is not found"""
    pass


class HSSOverloaded(Exception):
    """Exception to throw if a request cannot be completed because the HSS returns an
    overloaded response"""
    pass


class HSSGateway(object):
    """
    Gateway to real HSS. Abstracts away the underlying details of the Cx
    interface to enable fetching of data in a more HTTP-like fashion
    """
    def __init__(self, backend_callbacks):
        if not settings.HSS_ENABLED:
            raise HSSNotEnabled()

        dstack = stack.Stack()
        dstack.loadDictionary("cx", DICT_PATH)
        dstack.identity = settings.PUBLIC_HOSTNAME
        dstack.realm = settings.HS_HOSTNAME

        app = HSSAppListener(dstack, backend_callbacks)
        self.peer_listener = HSSPeerListener(app,
                                             settings.SIP_DIGEST_REALM,
                                             dstack)
        dstack.addSupportedVendor(10415)
        dstack.addSupportedVendor(13019)
        dstack.registerApplication(app, 0, 16777216)
        dstack.registerApplication(app, 10415, 16777216)
        dstack.registerApplication(app, 13019, 16777216)
        dstack.registerPeerListener(self.peer_listener)
        dstack.registerPeerIO(HSSPeerIO())
        dstack.clientV4Add(settings.HSS_IP, settings.HSS_PORT)

        # Twisted will run dstack.tick every second
        tick = LoopingCall(dstack.tick)
        tick.start(1)

    @defer.inlineCallbacks
    def get_digest(self, private_id, public_id):
        _log.debug("Getting auth for priv:%s pub:%s" % (private_id, public_id))
        result = yield self.peer_listener.fetch_multimedia_auth(private_id,
                                                                public_id)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_ims_subscription(self, private_id, public_id):
        _log.debug("Getting IMS subscription for priv:%s, pub:%s" %
                   (private_id, public_id))
        result = yield self.peer_listener.fetch_server_assignment(private_id,
                                                                  public_id)
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
        key = self.request_hash(answer)
        if key in self._pending_responses:
            _log.debug("Executing callbacks for pending requests %s" % hash(key))
            for deferred in self._pending_responses.pop(key):
                deferred.callback(answer)

    def onRequest(self, peer, request):
        try:
            if self.cx.isCommand(request, "Push-Profile"):
                self.onPushProfileRequest(peer, request)
            elif self.cx.isCommand(request, "Registration-Termination"):
                self.onRegistrationTerminationRequest(peer, request)
            else:
                answer = request.createAnswer()
                answer.addAVP(self.cx.getAVP("Result-Code").withInteger32(DIAMETER_COMMAND_UNSUPPORTED))
                peer.stack.sendByPeer(peer, answer)
        except:
            # We must catch and handle any exception here, as otherwise it will
            # propagate up to the Diameter stack and kill it.
            _log.exception("Caught exception while processing DIAMETER request")

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
        answer = request.createAnswer()
        result_code = self.cx.getAVP("Result-Code")
        d = defer.DeferredList(deferreds, fireOnOneErrback=True, consumeErrors=True)
        def success(result):
            answer.addAVP(result_code.withInteger32(DIAMETER_SUCCESS))
            peer.stack.sendByPeer(peer, answer)
        def failure(failure):
            _log.error("Push-Profile-Request failed with %s" % failure)
            answer.addAVP(result_code.withInteger32(DIAMETER_UNABLE_TO_COMPLY))
            peer.stack.sendByPeer(peer, answer)
        d.addCallbacks(success, failure)

    def onRegistrationTerminationRequest(self, peer, request):
        # Got a Registration-Termination-Request.  This tells us we won't get any
        # further notifications, so we should flush the cache now.
        answer = request.createAnswer()
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
        d = self.backend_callbacks.on_forced_expiry(private_ids, public_ids)
        # TODO: Notify Sprout to force deregistration there? 
        # Send the answer once the deferred is complete.
        result_code = self.cx.getAVP("Result-Code")
        def success(result):
            answer.addAVP(result_code.withInteger32(DIAMETER_SUCCESS))
            peer.stack.sendByPeer(peer, answer)
        def failure(failure):
            _log.error("Registration-Termination-Request failed with %s" % failure)
            answer.addAVP(result_code.withInteger32(DIAMETER_UNABLE_TO_COMPLY))
            peer.stack.sendByPeer(peer, answer)
        d.addCallbacks(success, failure)


class HSSPeerListener(stack.PeerListener):
    def __init__(self, app, domain, stack):
        self.app = app
        self.realm = domain
        self.server_name = "sip:%s:%d" % (settings.SPROUT_HOSTNAME, settings.SPROUT_PORT)
        self.cx = stack.getDictionary("cx")

    def connected(self, peer):
        _log.debug("Peer %s connected" % peer.identity)
        self.peer = peer

    def get_diameter_error_code(self, request):
        exp_result = self.cx.findFirstAVP(request, "Experimental-Result")
        if not exp_result:
            return None
        return exp_result.getGroup()[1].getInteger32()

    def log_diameter_error(self, msg):
        err_code = self.get_diameter_error_code(msg)
        if err_code:
            _log.info("HSS returned error code %d", err_code)
        else:
            _log.info("HSS returned error (code unknown)")

    @DeferTimeout.timeout(_loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_multimedia_auth(self, private_id, public_id):
        _log.debug("Sending Multimedia-Auth request for %s/%s" % (private_id, public_id))
        public_id = str(public_id)
        private_id = str(private_id)
        req = self.cx.getCommandRequest(self.peer.stack, "Multimedia-Auth", True)
        req.addAVP(self.cx.getAVP('User-Name').withOctetString(private_id))
        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(public_id))
        req.addAVP(self.cx.getAVP('Server-Name').withOctetString(self.server_name))
        req.addAVP(self.cx.getAVP('SIP-Number-Auth-Items').withInteger32(1))
        req.addAVP(self.cx.getAVP('SIP-Auth-Data-Item').withAVP(self.cx.getAVP('SIP-Authentication-Scheme').withOctetString('SIP Digest')))
        # Send off message to HSS
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d
        # Have response, parse out digest
        digest = self.cx.findFirstAVP(answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-HA1")
        if digest:
            defer.returnValue(digest.getOctetString())
        else:
            self.log_diameter_error(answer)
            # If the error is an Overload response, increment the HSS penalty counter
            if self.get_diameter_error_code(answer) == 3004:
                _penaltycounter.incr_hss_penalty_count()
                raise HSSOverloaded()
            else:
                raise HSSNotFound()

    @DeferTimeout.timeout(_loadmonitor.max_latency)
    @defer.inlineCallbacks
    def fetch_server_assignment(self, private_id, public_id):
        # Constants to match the enumerated values in 3GPP TS 29.229 s6.3.15
        REGISTRATION = 1
        NO_ASSIGNMENT = 0

        _log.debug("Sending Server-Assignment request for %s/%s" % (private_id, public_id))
        req = self.cx.getCommandRequest(self.peer.stack, "Server-Assignment", True)
        if private_id:
            # withOctetString takes a sequence of bytes, not a Unicode
            # string, so call bytes() on private_id and public_id
            req.addAVP(self.cx.getAVP('User-Name').withOctetString(bytes(private_id)))

        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(bytes(public_id)))
        req.addAVP(self.cx.getAVP('Server-Name').withOctetString(self.server_name))
        if private_id:
            req.addAVP(self.cx.getAVP('Server-Assignment-Type').withInteger32(REGISTRATION))
        else:
            req.addAVP(self.cx.getAVP('Server-Assignment-Type').withInteger32(NO_ASSIGNMENT))
        req.addAVP(self.cx.getAVP('Destination-Realm').withOctetString(self.realm))
        req.addAVP(self.cx.getAVP('User-Data-Already-Available').withInteger32(0))
        req.addAVP(self.cx.getAVP('Vendor-Specific-Application-Id'))
        req.addAVP(self.cx.getAVP('Auth-Session-State').withInteger32(0))
        # Send off message to HSS
        self.peer.stack.sendByPeer(self.peer, req)
        # Hook up our deferred to the callback
        d = defer.Deferred()
        self.app.add_pending_response(req, d)
        answer = yield d

        _log.debug("Received Server-Assignment response for %s:" % private_id)
        user_data = self.cx.findFirstAVP(answer, "User-Data")
        if not user_data:
            self.log_diameter_error(answer)
            # If the error is an Overload response, increment the HSS penalty counter
            if self.get_diameter_error_code(answer) == 3004:
                _penaltycounter.incr_hss_penalty_count()
                raise HSSOverloaded()
            else:
                raise HSSNotFound()

        defer.returnValue(user_data.getOctetString())

    def disconnected(self, peer):
        _log.debug("Peer %s disconnected" % peer.identity)
        self.peer = None
