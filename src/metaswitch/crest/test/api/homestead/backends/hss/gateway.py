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


import os
import mock
import unittest

from twisted.internet import defer
from twisted.python import failure
from diameter import stack

from metaswitch.crest import settings
from metaswitch.crest.test import matchers
from metaswitch.crest.api.base import penaltycounter
from metaswitch.crest.api.DeferTimeout import TimeoutError
from metaswitch.crest.api.homestead.backends.hss.gateway import HSSAppListener, HSSGateway, HSSNotEnabled, HSSPeerListener, HSSOverloaded

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
        self.backend_callbacks = mock.MagicMock()
        self.gateway = HSSGateway(self.backend_callbacks)

    def test_hss_enabled(self):
        settings.HSS_ENABLED = False
        self.assertRaises(HSSNotEnabled, HSSGateway, self.backend_callbacks)

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
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        self.peer_listener.fetch_multimedia_auth.return_value.callback(None)
        self.assertEquals(get_callback.call_args[0][0], None)

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
        self.backend_callbacks = mock.MagicMock()
        self.app_listener = HSSAppListener(stack, self.backend_callbacks)

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

class TestHSSAppListenerRequests(unittest.TestCase):
    """Tests HSSAppListener handling received requests - we use a live diameter for this"""
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.stack = stack.Stack()
        self.stack.identity = "ut-host"
        self.stack.realm = "ut-realm"
        self.stack.loadDictionary("cx", os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../../../api/homestead/backends/hss/dictionary.xml"))
        self.backend_callbacks = mock.MagicMock()
        self.app_listener = HSSAppListener(self.stack, self.backend_callbacks)
        self.cx = self.stack.getDictionary("cx")
        self.peer = mock.MagicMock()
        self.peer.stack = mock.MagicMock()
        self.peer.stack.sendByPeer = self.sendByPeer = mock.MagicMock()

    def send_request_in(self, command, avps=[]):
        self.request = self.cx.getCommandRequest(self.stack, command, True)
        self.request.addAVP(self.cx.getAVP("Vendor-Specific-Application-Id").withInteger32(1))
        self.request.addAVP(self.cx.getAVP("Auth-Session-State").withInteger32(1))
        self.request.addAVP(self.cx.getAVP("User-Name").withOctetString("priv"))
        for avp in avps:
            self.request.addAVP(avp)
        deferred = self.app_listener.onRequest(self.peer, self.request)
        self.on_request_callback = mock.MagicMock()
        deferred.addCallback(self.on_request_callback)

    def get_and_check_answer(self, result_code):
        self.assertEqual(self.sendByPeer.call_count, 1)
        answer = self.sendByPeer.call_args[0][1]
        self.assertEqual(self.request.command_code, answer.command_code)
        self.assertEqual(self.cx.findFirstAVP(answer, "Result-Code").getInteger32(), result_code)
        self.assertEqual(self.on_request_callback.call_count, 1)
        return answer

    def test_receive_push_profile_request_digest(self):
        self.backend_callbacks.on_digest_change.return_value = on_digest_change = defer.Deferred()
        avp = self.cx.getAVP("SIP-Auth-Data-Item").withAVP(
                self.cx.getAVP("SIP-Digest-Authenticate AVP").withAVP(
                  self.cx.getAVP("Digest-HA1").withOctetString(
                    "0123456789abcdef")))
        callback = self.send_request_in("Push-Profile", [avp])
        self.backend_callbacks.on_digest_change.assert_called_once_with("priv", "0123456789abcdef")
        on_digest_change.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_push_profile_request_digest_fail(self):
        self.backend_callbacks.on_digest_change.return_value = on_digest_change = defer.Deferred()
        avp = self.cx.getAVP("SIP-Auth-Data-Item").withAVP(
                self.cx.getAVP("SIP-Digest-Authenticate AVP").withAVP(
                  self.cx.getAVP("Digest-HA1").withOctetString(
                    "0123456789abcdef")))
        callback = self.send_request_in("Push-Profile", [avp])
        self.backend_callbacks.on_digest_change.assert_called_once_with("priv", "0123456789abcdef")
        on_digest_change.errback(failure.Failure(Exception()))
        self.get_and_check_answer(5012) # can't comply

    def test_receive_push_profile_request_user_data(self):
        self.backend_callbacks.on_ims_subscription_change.return_value = on_ims_subscription_change = defer.Deferred()
        callback = self.send_request_in("Push-Profile",
                                        [self.cx.getAVP("User-Data").withOctetString("xml")])
        self.backend_callbacks.on_ims_subscription_change.assert_called_once_with("xml")
        on_ims_subscription_change.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_push_profile_request_user_data_fail(self):
        self.backend_callbacks.on_ims_subscription_change.return_value = on_ims_subscription_change = defer.Deferred()
        callback = self.send_request_in("Push-Profile",
                                        [self.cx.getAVP("User-Data").withOctetString("xml")])
        self.backend_callbacks.on_ims_subscription_change.assert_called_once_with("xml")
        on_ims_subscription_change.errback(failure.Failure(Exception()))
        self.get_and_check_answer(5012) # can't comply

    def test_receive_registration_termination_request(self):
        self.backend_callbacks.on_forced_expiry.return_value = on_forced_expiry = defer.Deferred()
        callback = self.send_request_in("Registration-Termination",
                                        [self.cx.getAVP("Associated-Identities").withOctetString("priv2"),
                                         self.cx.getAVP("Public-Identity").withOctetString("pub1"),
                                         self.cx.getAVP("Public-Identity").withOctetString("pub2")])
        self.backend_callbacks.on_forced_expiry.assert_called_once_with(["priv", "priv2"], ["pub1", "pub2"])
        on_forced_expiry.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_registration_termination_request_fail(self):
        self.backend_callbacks.on_forced_expiry.return_value = on_forced_expiry = defer.Deferred()
        callback = self.send_request_in("Registration-Termination",
                                        [self.cx.getAVP("Associated-Identities").withOctetString("priv2"),
                                         self.cx.getAVP("Public-Identity").withOctetString("pub1"),
                                         self.cx.getAVP("Public-Identity").withOctetString("pub2")])
        self.backend_callbacks.on_forced_expiry.assert_called_once_with(["priv", "priv2"], ["pub1", "pub2"])
        on_forced_expiry.errback(failure.Failure(Exception()))
        self.get_and_check_answer(5012) # can't comply

    def test_receive_unsupported_command(self):
        self.send_request_in("Multimedia-Auth")
        self.get_and_check_answer(3001) # unsupported

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

        penaltycounter._log = mock.MagicMock()
        penaltycounter.reset_hss_penalty_count()

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
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth,
                             expected_retval=matchers.MatchesNone())


    def test_fetch_multimedia_auth_not_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth,
                             error_code=3005,
                             expected_retval=matchers.MatchesNone())


    def test_fetch_multimedia_auth_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_multimedia_auth,
                             error_code=3004,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

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

    def test_fetch_server_assignment_no_priv(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_server_assignment(None, "pub")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Server-Assignment", True)
        self.assertEquals(mock_req.avps,
                          [{'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 0},
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
        self.common_test_hss(self.peer_listener.fetch_server_assignment,
                             expected_retval=matchers.MatchesNone())

    def test_fetch_server_assignment_not_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_server_assignment,
                             error_code=3005,
                             expected_retval=matchers.MatchesNone())


    def test_fetch_server_assignment_overload_error_code(self):
        self.common_test_hss(self.peer_listener.fetch_server_assignment,
                             error_code=3004,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

    def common_test_hss(self,
                        function,
                        first_avp=None,
                        error_code=None,
                        expected_exception=None,
                        expected_retval=matchers.MatchesAnything(),
                        expected_count=0):
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

        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        deferred_errback = mock.MagicMock()
        deferred.addErrback(deferred_errback)
        inner_deferred.callback(mock_answer)

        if expected_exception:
            self.assertEquals(deferred_callback.called, False)
            self.assertEquals(deferred_errback.called, True)
            self.assertEquals(deferred_errback.call_args[0][0].type, expected_exception)
        else:
            self.assertEquals(deferred_callback.called, True)
            self.assertEquals(deferred_errback.called, False)
            self.assertEquals(deferred_callback.call_args[0][0], expected_retval)

        # The penalty counter should be at 1
        self.assertEquals(penaltycounter.get_hss_penalty_count(), expected_count)

    def test_disconnected(self):
        self.assertEquals(self.peer_listener.peer, self.peer)
        self.peer_listener.disconnected(mock.MagicMock())
        self.assertEquals(self.peer_listener.peer, None)
