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
from xml.etree import ElementTree

from metaswitch.crest import settings
from metaswitch.crest.api.homestead.hss.io import HSSPeerIO

_log = logging.getLogger("crest.api.homestead.hss")

DICT_NAME = "dictionary.xml"
DICT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), DICT_NAME)

# HSS-specific Exceptions
class HSSNotEnabled(Exception):
    """Exception to throw if gateway is created without HSS_ENABLED set to true"""
    pass

class HSSNotFound(Exception):
    """Exception to throw if a request cannot be completed because a resource is not found"""
    pass

class HSSGateway(stack.ApplicationListener):
    """
    Gateway to real HSS. Abstracts away the underlying details of the Cx interface
    to enable fetching of data in a more HTTP-like fashion
    """
    def __init__(self):
        if not settings.HSS_ENABLED:
            raise HSSNotEnabled()
        
        dstack = stack.Stack()
        dstack.loadDictionary("cx", DICT_PATH)
        dstack.identity = "sip:%s" % settings.SIP_DIGEST_REALM
        dstack.realm = settings.SIP_DIGEST_REALM

        app = HSSAppListener(dstack)
        self.peer_listener = HSSPeerListener(app, 
                                             settings.SIP_DIGEST_REALM,
                                             dstack)
        
        dstack.registerApplication(app, 0, 16777216)
        dstack.registerPeerListener(self.peer_listener)
        dstack.registerPeerIO(HSSPeerIO())
        dstack.clientV4Add(settings.HSS_IP, settings.HSS_PORT)

        # Twisted will run dstack.tick every second
        tick = LoopingCall(dstack.tick)
        tick.start(1)
    
    @defer.inlineCallbacks
    def get_digest(self, private_id, public_id):
        _log.debug("Getting auth for priv:%s pub:%s"  % (private_id, public_id))
        result = yield self.peer_listener.fetch_multimedia_auth(private_id, public_id)
        defer.returnValue(result)
    
    @defer.inlineCallbacks
    def get_ifc(self, private_id, public_id):
        _log.debug("Getting IFC for priv:%s pub:%s"  % (private_id, public_id))
        result = yield self.peer_listener.fetchIFC(private_id, public_id)
        defer.returnValue(result)
    
class HSSAppListener(stack.ApplicationListener):
    """
    The HSSAppListener maintains a list of pending requests outstanding on the HSS
    (stored as deferreds), and listens for responses from the HSS. When a response
    arrives, it correlates it with a pending request and injects the response into
    the pending request
    """
    def __init__(self, stack):
        self._pending_responses = {}
        self.cx = stack.getDictionary("cx")

    def add_pending_response(self, request, deferred):
        key = self.request_hash(request)
        existing_responses = self._pending_responses.setdefault(key, [])
        _log.debug("Adding request %s to pending responses" % hash(key))
        existing_responses.append(deferred)

    def request_hash(self, request):
        # To ensure we can correlate requests with this callback, key off the request
        # in a identifiable way. eTe is the request's end-to-end identifier
        return (request.application_id, request.command_code, request.eTe)

    def onAnswer(self, peer, answer):
        key = self.request_hash(answer)
        if key in self._pending_responses:
            _log.debug("Executing callbacks for pending requests %s" % hash(key))
            for deferred in self._pending_responses.pop(key):
                deferred.callback(answer)

class HSSPeerListener(stack.PeerListener):
    def __init__(self, app, domain, stack):
        self.app = app
        self.realm = domain
        self.server_name = "%s:%d" % (settings.SPROUT_HOSTNAME, settings.SPROUT_PORT)
        self.cx = stack.getDictionary("cx")

    def connected(self, peer):
        _log.debug("Peer %s connected" % peer.identity)
        self.peer = peer

    def get_diameter_error_code(self, request):
        exp_result = self.cx.findFirstAVP(request, "Experimental-Result")
        if not exp_result:
            return None
        return exp_result.getGroup()[1].getInteger32()

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
            _log.info("HSS returned error code %d", self.get_diameter_error_code(answer))
            raise HSSNotFound()

    @defer.inlineCallbacks
    def fetchIFC(self, private_id, public_id):
        _log.debug("Sending Server-Assignment request for %s/%s" % (private_id, public_id))
        public_id = str(public_id)
        private_id = str(private_id)
        req = self.cx.getCommandRequest(self.peer.stack, "Server-Assignment", True)
        req.addAVP(self.cx.getAVP('User-Name').withOctetString(private_id))
        req.addAVP(self.cx.getAVP('Public-Identity').withOctetString(public_id))
        req.addAVP(self.cx.getAVP('Server-Name').withOctetString(self.server_name))
        req.addAVP(self.cx.getAVP('Server-Assignment-Type').withInteger32(1))
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
            _log.info("HSS returned error code %d", self.get_diameter_error_code(answer))
            raise HSSNotFound()
        xml = ElementTree.fromstring(user_data.getOctetString())
        # Iterate over all nodes in xml, returning the one matching the correct
        # public id
        for sp in xml.iterfind('./ServiceProfile'):
            if public_id == sp.find('./PublicIdentity/Identity').text:
                # Note that returnValue is the standard method of returning from 
                # defer.inlineCallbacks decorated generators, so that once a public
                # id is returned the generator will terminate
                defer.returnValue(ElementTree.tostring(sp))
        # If none match, throw. 
        _log.info("No matching IFCs found for public id %s" % public_id)
        raise HSSNotFound()

    def disconnected(self, peer):
        _log.debug("Peer %s disconnected" % peer.identity)
        self.peer = None
