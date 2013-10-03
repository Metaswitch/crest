#!/usr/bin/python

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


import httplib
import mock
import unittest

from mock import ANY
from twisted.internet import defer
from twisted.python.failure import Failure

from metaswitch.crest import settings
from metaswitch.crest.api._base import _penaltycounter
from metaswitch.crest.api.DeferTimeout import TimeoutError
from metaswitch.crest.api.homestead.backends.hss.gateway import HSSAppListener, HSSGateway, HSSNotFound, HSSNotEnabled, HSSPeerListener, HSSOverloaded

class TestHSSGateway(unittest.TestCase):
    """
    Detailed, isolated unit tests of the HSSGateway class.
    """
    @mock.patch("metaswitch.crest.api.homestead.backends.hss.gateway.HSSAppListener")
    @mock.patch("metaswitch.crest.api.homestead.backends.hss.gateway.HSSPeerListener")
    @mock.patch("diameter.stack")
    def setUp(self, stack, HSSPeerListener, HSSAppListener):
        unittest.TestCase.setUp(self)

        self.dstack = mock.MagicMock()
        stack.Stack.return_value = self.dstack
        self.peer_listener = mock.MagicMock()
        HSSPeerListener.return_value = self.peer_listener
        self.app_listener = mock.MagicMock()
        HSSAppListener.return_value = self.app_listener

        settings.PASSWORD_ENCRYPTION_KEY = "TOPSECRET"
        settings.HSS_ENABLED = True
        settings.HSS_IP = "example.com"
        settings.HSS_PORT = 3868
        self.gateway = HSSGateway()

    def test_hss_enabled(self):
        settings.HSS_ENABLED = False
        self.assertRaises(HSSNotEnabled, HSSGateway)

    # There is a fair amount of code here, for testing what is essentially a
    # pretty simple function. The verbosity comes from correctly mocking out
    # the deferred inlineCallbacks decorated functions, which are inherently
    # more complex than standard functions - even if they appear similar.
    # These tests also act as a good example of testing inlineCallback functions,
    # with the same techniques applied to more complicated functions later
    def test_get_digest(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_digest("priv", "pub")
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        self.peer_listener.fetch_multimedia_auth.return_value.callback("digest")
        self.assertEquals(get_callback.call_args[0][0], "digest")

    def test_get_digest_not_found(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_digest("priv", "pub")
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.peer_listener.fetch_multimedia_auth.return_value.errback(HSSNotFound())
        self.assertEquals(get_errback.call_args[0][0].type, HSSNotFound)

    def test_get_digest_timeout(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_digest("priv", "pub")
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.peer_listener.fetch_multimedia_auth.return_value.errback(TimeoutError())
        self.assertEquals(get_errback.call_args[0][0].type, TimeoutError)

class TestHSSAppListener(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.cx = mock.MagicMock()
        stack = mock.MagicMock()
        stack.getDictionary.return_value = self.cx
        self.app_listener = HSSAppListener(stack)

        self.request = mock.MagicMock()
        self.request.application_id = "app_id"
        self.request.command_code = "command_code"
        self.request.eTe = "E.T. phone home"

    def test_request_hash(self):
        self.assertEquals(self.app_listener.request_hash(self.request),
                     ("app_id", "command_code", "E.T. phone home"))


    def test_add_pending_response(self):
        deferred = defer.Deferred()
        self.app_listener.add_pending_response(self.request, deferred)
        self.assertEquals({("app_id", "command_code", "E.T. phone home"): [deferred]},
                          self.app_listener._pending_responses)
        # Simluate an answer to verify that the deferred is called
        callback = mock.MagicMock()
        deferred.addCallback(callback)
        self.app_listener.onAnswer(None, self.request)
        self.assertEquals(callback.call_args[0][0], self.request)

class TestHSSPeerListener(unittest.TestCase):
    class MockRequest(mock.MagicMock):
        def __init__(self):
            mock.MagicMock.__init__(self)
            self.avps = []

        def addAVP(self, avp):
            self.avps.append(avp)

    class MockCx(mock.MagicMock):
        class MockAVP(mock.MagicMock):
            def __init__(self, avp, value=None):
                mock.MagicMock.__init__(self)
                self.avp = avp
                self.value = value

            def withOctetString(self, s):
                return {self.avp: s}

            def withInteger32(self, i):
                return {self.avp: i}

            def withAVP(self, avp):
                return {self.avp: avp}

        def getAVP(self, avp):
            if avp == 'Vendor-Specific-Application-Id':
                return {avp: None}
            return self.MockAVP(avp)

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.cx = self.MockCx()
        stack = mock.MagicMock()
        stack.getDictionary.return_value = self.cx
        self.app = mock.MagicMock()

        self.peer_listener = HSSPeerListener(self.app, "domain", stack)
        self.peer = mock.MagicMock()
        self.peer_listener.connected(self.peer)
        self.assertEquals(self.peer, self.peer_listener.peer)
        settings.SPROUT_HOSTNAME = "sprout"
        settings.SPROUT_PORT = 1234

        _penaltycounter._log = mock.MagicMock()
        _penaltycounter.reset_hss_penalty_count()

    def test_get_diameter_error_code(self):
        mock_error = mock.MagicMock()
        mock_error.getInteger32.return_value = 1234
        mock_exp = mock.MagicMock()
        mock_exp.getGroup.return_value = [None, mock_error]
        self.cx.findFirstAVP.return_value = mock_exp
        request = mock.MagicMock()

        error_code = self.peer_listener.get_diameter_error_code(request)
        self.cx.findFirstAVP.assert_called_once_with(request, "Experimental-Result")
        mock_exp.getGroup.assert_called_once_with()
        mock_error.getInteger32.assert_called_once_with()
        self.assertEquals(1234, error_code)

        self.cx.findFirstAVP.return_value = None
        error_code = self.peer_listener.get_diameter_error_code(request)
        self.assertEquals(None, error_code)

    def test_fetch_multimedia_auth(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_multimedia_auth("priv", "pub")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Multimedia-Auth", True)
        self.assertEquals(mock_req.avps,
                          [{'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'SIP-Number-Auth-Items': 1},
                           {'SIP-Auth-Data-Item': {'SIP-Authentication-Scheme': 'SIP Digest'}}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.return_value = mock.MagicMock()
        self.cx.findFirstAVP.return_value.getOctetString.return_value = "digest"
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        self.cx.findFirstAVP.assert_called_once_with(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-HA1")
        self.assertEquals(deferred_callback.call_args[0][0], "digest")

    def test_fetch_multimedia_auth_no_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth, None, None, HSSNotFound, 0)

    def test_fetch_multimedia_auth_not_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth, None, 3005, HSSNotFound, 0)

    def test_fetch_multimedia_auth_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth, None, 3004, HSSOverloaded, 1)

    def test_fetch_server_assignment(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_server_assignment("priv", "pub")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Server-Assignment", True)
        self.assertEquals(mock_req.avps,
                          [{'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 1},
                           {'Destination-Realm': 'domain'},
                           {'User-Data-Already-Available': 0},
                           {'Vendor-Specific-Application-Id': None},
                           {'Auth-Session-State': 0}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<IMSSubscription>"
          "<PrivateID>priv</PrivateID>"
          "<ServiceProfile>"
            "<PublicIdentity>"
              "<Identity>pub</Identity>"
              "<Extension>"
                "<IdentityType>0</IdentityType>"
              "</Extension>"
            "</PublicIdentity>"
            "<InitialFilterCriteria>"
              "ifc"
            "</InitialFilterCriteria>"
          "</ServiceProfile>"
        "</IMSSubscription>")
        self.cx.findFirstAVP.return_value = mock.MagicMock()
        self.cx.findFirstAVP.return_value.getOctetString.return_value = xml
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        self.cx.findFirstAVP.assert_called_once_with(mock_answer, "User-Data")
        self.assertEquals(deferred_callback.call_args[0][0], xml)

    def test_fetch_server_assignment_multi(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_server_assignment("priv", "pub")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Server-Assignment", True)
        self.assertEquals(mock_req.avps,
                          [{'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 1},
                           {'Destination-Realm': 'domain'},
                           {'User-Data-Already-Available': 0},
                           {'Vendor-Specific-Application-Id': None},
                           {'Auth-Session-State': 0}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<IMSSubscription>"
          "<PrivateID>priv</PrivateID>"
          "<ServiceProfile>"
            "<PublicIdentity>"
              "<Identity>pub</Identity>"
              "<Extension>"
                "<IdentityType>0</IdentityType>"
              "</Extension>"
            "</PublicIdentity>"
            "<PublicIdentity>"
              "<Identity>pub2</Identity>"
              "<Extension>"
                "<IdentityType>0</IdentityType>"
              "</Extension>"
            "</PublicIdentity>"
            "<InitialFilterCriteria>"
              "ifc"
            "</InitialFilterCriteria>"
          "</ServiceProfile>"
        "</IMSSubscription>")
        self.cx.findFirstAVP.return_value = mock.MagicMock()
        self.cx.findFirstAVP.return_value.getOctetString.return_value = xml
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        self.cx.findFirstAVP.assert_called_once_with(mock_answer, "User-Data")
        self.assertEquals(deferred_callback.call_args[0][0], xml)

    def test_fetch_server_assignment_no_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_server_assignment, None, None, HSSNotFound, 0)

    def test_fetch_server_assignment_not_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_server_assignment, None, 3005, HSSNotFound, 0)

    def test_fetch_server_assignment_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_server_assignment, None, 3004, HSSOverloaded, 1)

    def common_test_hss(self, function, first_avp, error_code, expected_exception, expected_count):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = function("priv", "pub")
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic an error returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.return_value = first_avp
        # Set the error code to the overload response
        err_code = mock.MagicMock()
        err_code.return_value = error_code
        self.peer_listener.get_diameter_error_code = err_code
        deferred_errback = mock.MagicMock()
        deferred.addErrback(deferred_errback)
        inner_deferred.callback(mock_answer)
        self.assertEquals(deferred_errback.call_args[0][0].type, expected_exception)
        # The penalty counter should be at 1
        self.assertEquals(_penaltycounter.get_hss_penalty_count(), expected_count)

    def test_disconnected(self):
        self.assertEquals(self.peer_listener.peer, self.peer)
        self.peer_listener.disconnected(mock.MagicMock())
        self.assertEquals(self.peer_listener.peer, None)
