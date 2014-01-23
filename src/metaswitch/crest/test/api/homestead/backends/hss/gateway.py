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

import metaswitch.crest.api.base as base
from metaswitch.crest import settings
from metaswitch.crest.test import matchers
from metaswitch.crest.api.homestead.auth_vectors import DigestAuthVector, AKAAuthVector
from metaswitch.crest.api.base import penaltycounter
from metaswitch.crest.api.DeferTimeout import TimeoutError
from metaswitch.crest.api.homestead.backends.hss.gateway import HSSAppListener, HSSGateway, HSSNotEnabled, HSSPeerListener, HSSOverloaded, UserNotIdentifiable, UserNotAuthorized
from metaswitch.crest.api.homestead import authtypes
from metaswitch.crest.api.homestead import resultcodes
from metaswitch.crest.api.homestead.cache.handlers import AUTH_TYPES, ORIGINATING

from base64 import b64encode
from binascii import hexlify

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
    def test_get_av_digest(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.SIP_DIGEST)
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.SIP_DIGEST, None)
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        auth = DigestAuthVector("ha1", "example.com", "auth", True)
        self.peer_listener.fetch_multimedia_auth.return_value.callback(auth)
        self.assertEquals(get_callback.call_args[0][0], auth)

    def test_get_av_unknown(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.UNKNOWN)
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.UNKNOWN, None)
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        auth = DigestAuthVector("ha1", "example.com", "auth", True)
        self.peer_listener.fetch_multimedia_auth.return_value.callback(auth)
        self.assertEquals(get_callback.call_args[0][0], auth)

    def test_get_av_aka(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.AKA)
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.AKA, None)
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        auth = AKAAuthVector("challenge", "response", "ck", "ik")
        self.peer_listener.fetch_multimedia_auth.return_value.callback(auth)
        self.assertEquals(get_callback.call_args[0][0], auth)

    def test_get_av_aka_with_autn(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.AKA, "autn")
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.AKA, "autn")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        auth = AKAAuthVector("challenge", "response", "ck", "ik")
        self.peer_listener.fetch_multimedia_auth.return_value.callback(auth)
        self.assertEquals(get_callback.call_args[0][0], auth)

    def test_get_av_not_found(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.UNKNOWN)
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.UNKNOWN, None)
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        self.peer_listener.fetch_multimedia_auth.return_value.callback(None)
        self.assertEquals(get_callback.call_args[0][0], None)

    def test_get_av_timeout(self):
        self.peer_listener.fetch_multimedia_auth.return_value = defer.Deferred()
        get_deferred = self.gateway.get_av("priv", "pub", authtypes.SIP_DIGEST)
        self.peer_listener.fetch_multimedia_auth.assert_called_once_with("priv", "pub", authtypes.SIP_DIGEST, None)
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
        self.stack.sendByPeer = self.sendByPeer = mock.MagicMock()
        self.backend_callbacks = mock.MagicMock()
        self.app_listener = HSSAppListener(self.stack, self.backend_callbacks)
        self.cx = self.stack.getDictionary("cx")
        self.peer = mock.MagicMock()
        self.peer.stack = self.stack

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
        self.send_request_in("Push-Profile", [avp])
        self.backend_callbacks.on_digest_change.assert_called_once_with("priv", "0123456789abcdef")
        on_digest_change.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_push_profile_request_digest_fail(self):
        self.backend_callbacks.on_digest_change.return_value = on_digest_change = defer.Deferred()
        avp = self.cx.getAVP("SIP-Auth-Data-Item").withAVP(
                self.cx.getAVP("SIP-Digest-Authenticate AVP").withAVP(
                  self.cx.getAVP("Digest-HA1").withOctetString(
                    "0123456789abcdef")))
        self.send_request_in("Push-Profile", [avp])
        self.backend_callbacks.on_digest_change.assert_called_once_with("priv", "0123456789abcdef")
        on_digest_change.errback(failure.Failure(Exception()))
        self.get_and_check_answer(5012) # can't comply

    def test_receive_push_profile_request_user_data(self):
        self.backend_callbacks.on_ims_subscription_change.return_value = on_ims_subscription_change = defer.Deferred()
        self.send_request_in("Push-Profile",
                             [self.cx.getAVP("User-Data").withOctetString("xml")])
        self.backend_callbacks.on_ims_subscription_change.assert_called_once_with("xml")
        on_ims_subscription_change.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_push_profile_request_user_data_fail(self):
        self.backend_callbacks.on_ims_subscription_change.return_value = on_ims_subscription_change = defer.Deferred()
        self.send_request_in("Push-Profile",
                             [self.cx.getAVP("User-Data").withOctetString("xml")])
        self.backend_callbacks.on_ims_subscription_change.assert_called_once_with("xml")
        on_ims_subscription_change.errback(failure.Failure(Exception()))
        self.get_and_check_answer(5012) # can't comply

    def test_receive_registration_termination_request(self):
        self.backend_callbacks.on_forced_expiry.return_value = on_forced_expiry = defer.Deferred()
        self.send_request_in("Registration-Termination",
                             [self.cx.getAVP("Associated-Identities").withOctetString("priv2"),
                              self.cx.getAVP("Public-Identity").withOctetString("pub1"),
                              self.cx.getAVP("Public-Identity").withOctetString("pub2")])
        self.backend_callbacks.on_forced_expiry.assert_called_once_with(["priv", "priv2"], ["pub1", "pub2"])
        on_forced_expiry.callback(None)
        self.get_and_check_answer(2001) # success

    def test_receive_registration_termination_request_fail(self):
        self.backend_callbacks.on_forced_expiry.return_value = on_forced_expiry = defer.Deferred()
        self.send_request_in("Registration-Termination",
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
            self.avps.append(avp.get_self())

    class MockCx(mock.MagicMock):
        class MockAVP(mock.MagicMock):
            def __init__(self, avp, value="SENTINEL"):
                mock.MagicMock.__init__(self)
                self.avp = avp
                self.avps = []
                self.value = value

            def withOctetString(self, s):
                self.value = s
                return self

            def withInteger32(self, i):
                self.value = i
                return self

            def withAVP(self, avp):
                self.value = "SENTINEL"
                self.avps.append(avp)
                return self

            def addAVP(self, avp):
                self.value = "SENTINEL"
                self.avps.append(avp.get_self())

            def get_self(self):
                if self.value != "SENTINEL":
                    return {self.avp: self.value}
                else:
                    return {self.avp: self.avps}

        def getAVP(self, avp):
            if avp == 'Vendor-Specific-Application-Id':
                return self.MockAVP(avp, None)
            return self.MockAVP(avp)

    class FakeAVP(mock.MagicMock):
        def __init__(self, avp, *args, **kwargs):
            mock.MagicMock.__init__(self, args, kwargs)
            self.avp = avp

        def getOctetString(self):
            return self.avp

    @mock.patch("time.time")
    def setUp(self, time):
        unittest.TestCase.setUp(self)
        self.cx = self.MockCx()
        stack = mock.MagicMock()
        stack.getDictionary.return_value = self.cx
        self.app = mock.MagicMock()
        time.return_value = 1234

        self.peer_listener = HSSPeerListener(self.app, "domain", stack)
        self.peer = mock.MagicMock()
        self.peer.identity = 'peer-host'
        self.peer.realm = 'peer-realm'
        self.peer_listener.connected(self.peer)
        self.assertEquals(self.peer, self.peer_listener.peer)
        settings.SPROUT_HOSTNAME = "sprout"
        settings.SPROUT_PORT = 1234

        penaltycounter._log = mock.MagicMock()
        penaltycounter.reset_hss_penalty_count()

        # Mock out zmq so we don't fail if we try to report stats during the
        # test.
        self.real_zmq = base.zmq
        base.zmq = mock.MagicMock()

    def tearDown(self):
        base.zmq = self.real_zmq
        del self.real_zmq

    # Change the return value of findFirstAVP depending on its arguments.
    def digest_arg(self, *params):
        request_args = {"SIP-Authentication-Scheme": self.FakeAVP("SIP Digest"),
                        "Digest-HA1": self.FakeAVP("Ha1"),
                        "Digest-Realm": self.FakeAVP("realm.com"),
                        "Digest-QoP": self.FakeAVP("QoP")}

        for arg in params:
            if arg in request_args:
                return request_args[arg]

    def aka_arg(self, *params):
        request_args = {"SIP-Authentication-Scheme": self.FakeAVP("Digest-AKAv1-MD5"),
                        "Confidentiality-Key": self.FakeAVP("ck"),
                        "Integrity-Key": self.FakeAVP("ik"),
                        "SIP-Authenticate": self.FakeAVP("rand"),
                        "SIP-Authorization": self.FakeAVP("xres")}

        for arg in params:
            if arg in request_args:
                return request_args[arg]

    def test_get_diameter_result_code(self):
        mock_error = mock.MagicMock()
        mock_error.getInteger32.return_value = 1234
        self.cx.findFirstAVP.return_value = mock_error
        request = mock.MagicMock()

        error_code = self.peer_listener.get_diameter_result_code(request)
        self.cx.findFirstAVP.assert_called_once_with(request, "Result-Code")
        mock_error.getInteger32.assert_called_once_with()
        self.assertEquals(1234, error_code)

        self.cx.findFirstAVP.return_value = None
        error_code = self.peer_listener.get_diameter_result_code(request)
        self.assertEquals(None, error_code)

    def test_get_diameter_exp_result_code(self):
        mock_error = mock.MagicMock()
        mock_error.getInteger32.return_value = 1234
        mock_exp = mock.MagicMock()
        mock_exp.getGroup.return_value = [None, mock_error]
        self.cx.findFirstAVP.return_value = mock_exp
        request = mock.MagicMock()

        error_code = self.peer_listener.get_diameter_exp_result_code(request)
        self.cx.findFirstAVP.assert_called_once_with(request, "Experimental-Result")
        mock_exp.getGroup.assert_called_once_with()
        mock_error.getInteger32.assert_called_once_with()
        self.assertEquals(1234, error_code)

        self.cx.findFirstAVP.return_value = None
        error_code = self.peer_listener.get_diameter_exp_result_code(request)
        self.assertEquals(None, error_code)

    def test_get_diameter_exp_result_vendor(self):
        mock_vendor = mock.MagicMock()
        mock_vendor.getInteger32.return_value = 1111
        mock_exp = mock.MagicMock()
        mock_exp.getGroup.return_value = [mock_vendor, None]
        self.cx.findFirstAVP.return_value = mock_exp
        request = mock.MagicMock()

        vendor = self.peer_listener.get_diameter_exp_result_vendor(request)
        self.cx.findFirstAVP.assert_called_once_with(request, "Experimental-Result")
        mock_exp.getGroup.assert_called_once_with()
        mock_vendor.getInteger32.assert_called_once_with()
        self.assertEquals(1111, vendor)

    def test_fetch_multimedia_auth_digest(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.SIP_DIGEST, None)
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Multimedia-Auth", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'SIP-Number-Auth-Items': 1},
                           {'SIP-Auth-Data-Item': [{'SIP-Authentication-Scheme': 'SIP Digest'}]}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.side_effect = self.digest_arg
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        # Check the findFirstAVP calls are correct
        calls = [mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authentication-Scheme"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-HA1"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-Realm"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-QoP")]
        self.cx.findFirstAVP.assert_has_calls(calls)

        # Check the correct authentication vector is returned
        expected = {"digest": {"ha1": "Ha1", "realm": "realm.com", "qop": "QoP"}}
        self.assertEquals(deferred_callback.call_args[0][0].to_json(), expected)

    def test_fetch_multimedia_auth_unknown(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.UNKNOWN, None)
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Multimedia-Auth", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'SIP-Number-Auth-Items': 1},
                           {'SIP-Auth-Data-Item': [{'SIP-Authentication-Scheme': 'Unknown'}]}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.side_effect = self.digest_arg
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        # Check the findFirstAVP calls are correct
        calls = [mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authentication-Scheme"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-HA1"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-Realm"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-QoP")]
        self.cx.findFirstAVP.assert_has_calls(calls)

        # Check the correct authentication vector is returned
        expected = {"digest": {"ha1": "Ha1", "realm": "realm.com", "qop": "QoP"}}
        self.assertEquals(deferred_callback.call_args[0][0].to_json(), expected)

    def test_fetch_multimedia_auth_unknown_interop(self):
        settings.LOWERCASE_UNKNOWN = True
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.UNKNOWN, None)
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Multimedia-Auth", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'SIP-Number-Auth-Items': 1},
                           {'SIP-Auth-Data-Item': [{'SIP-Authentication-Scheme': 'unknown'}]}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.side_effect = self.digest_arg
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        # Check the findFirstAVP calls are correct
        calls = [mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authentication-Scheme"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-HA1"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-Realm"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Digest-Authenticate AVP", "Digest-QoP")]
        self.cx.findFirstAVP.assert_has_calls(calls)

        # Check the correct authentication vector is returned
        expected = {"digest": {"ha1": "Ha1", "realm": "realm.com", "qop": "QoP"}}
        self.assertEquals(deferred_callback.call_args[0][0].to_json(), expected)

    def test_fetch_multimedia_auth_aka(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.AKA, "autn")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Multimedia-Auth", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'SIP-Number-Auth-Items': 1},
                           {'SIP-Auth-Data-Item': [{'SIP-Authentication-Scheme': 'Digest-AKAv1-MD5'}, {'SIP-Authorization': 'autn'}]}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.side_effect = self.aka_arg
        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)

        # Check the findFirstAVP calls are correct
        calls = [mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authentication-Scheme"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "Confidentiality-Key"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "Integrity-Key"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authorization"),
                 mock.call(mock_answer, "SIP-Auth-Data-Item", "SIP-Authenticate")]
        self.cx.findFirstAVP.assert_has_calls(calls)

        # Check the correct authentication vector is returned
        expected = {"aka": {"challenge": b64encode("rand"),
                            "cryptkey": hexlify("ck"),
                            "integritykey": hexlify("ik"),
                            "response": hexlify("xres")}}
        self.assertEquals(deferred_callback.call_args[0][0].to_json(), expected)

    def test_fetch_multimedia_auth_no_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.SIP_DIGEST, None),
                             expected_retval=matchers.MatchesNone())

    def test_fetch_multimedia_auth_not_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.SIP_DIGEST, None),
                             result_code=3005,
                             expected_retval=matchers.MatchesNone())


    def test_fetch_multimedia_auth_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_multimedia_auth("priv", "pub", authtypes.SIP_DIGEST, None),
                             result_code=resultcodes.DIAMETER_TOO_BUSY,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

    def test_fetch_server_assignment(self):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_server_assignment("priv", "pub")
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Server-Assignment", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 1},
                           {'User-Data-Already-Available': 0}])
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
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 3},
                           {'User-Data-Already-Available': 0}])
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
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'User-Name': 'priv'},
                           {'Public-Identity': 'pub'},
                           {'Server-Name': 'sip:sprout:1234'},
                           {'Server-Assignment-Type': 1},
                           {'User-Data-Already-Available': 0}])
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
        self.common_test_hss(lambda: self.peer_listener.fetch_server_assignment("priv", "pub"),
                             expected_retval=matchers.MatchesNone())

    def test_fetch_server_assignment_not_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_server_assignment("priv", "pub"),
                             result_code=3005,
                             expected_retval=matchers.MatchesNone())

    def test_fetch_server_assignment_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_server_assignment("priv", "pub"),
                             result_code=resultcodes.DIAMETER_TOO_BUSY,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

    def test_fetch_user_auth_success_scscf(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                 scscf="scscf")

    def test_fetch_user_auth_success_scscf_and_capabilities(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                 scscf="scscf",
                                                 man_capabilities=[4,9,7],
                                                 opt_capabilities=[5,6])

    def test_fetch_user_auth_success_capabilities(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                 man_capabilities=[4,9,7],
                                                 opt_capabilities=[5,6])

    def test_fetch_user_auth_success_man_capabilities(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                 man_capabilities=[4,9,7])

    def test_fetch_user_auth_success_opt_capabilities(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                 opt_capabilities=[4,9,7])

    def test_fetch_user_auth_success_no_data(self):
        self.common_test_fetch_user_auth_success(result_code=resultcodes.DIAMETER_SUCCESS)

    def test_fetch_user_auth_success_first_reg(self):
        self.common_test_fetch_user_auth_success(experimental_result_code=resultcodes.DIAMETER_FIRST_REGISTRATION)

    def test_fetch_user_auth_success_sub_reg(self):
        self.common_test_fetch_user_auth_success(experimental_result_code=resultcodes.DIAMETER_SUBSEQUENT_REGISTRATION)

    def test_fetch_user_auth_no_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             expected_retval=matchers.MatchesNone())

    def test_fetch_user_auth_user_unknown_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             experimental_result_code=resultcodes.DIAMETER_ERROR_USER_UNKNOWN,
                             expected_exception=UserNotIdentifiable)

    def test_fetch_user_auth_no_identity_match_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             experimental_result_code=resultcodes.DIAMETER_ERROR_IDENTITIES_DONT_MATCH,
                             expected_exception=UserNotIdentifiable)

    def test_fetch_user_auth_authorization_rej_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             experimental_result_code=resultcodes.DIAMETER_ERROR_ROAMING_NOT_ALLOWED,
                             expected_exception=UserNotAuthorized)

    def test_fetch_user_auth_roaming_not_allowed_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             result_code=resultcodes.DIAMETER_AUTHORIZATION_REJECTED,
                             expected_exception=UserNotAuthorized)

    def test_fetch_user_auth_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             result_code=resultcodes.DIAMETER_TOO_BUSY,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

    def test_fetch_user_auth_other_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", AUTH_TYPES["REG"]),
                             result_code=3005,
                             expected_retval=matchers.MatchesNone())

    def test_fetch_location_info_success_scscf(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                     scscf="scscf")

    def test_fetch_location_info_success_scscf_and_capabilities(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                     scscf="scscf",
                                                     man_capabilities=[4,9,7],
                                                     opt_capabilities=[5,6])

    def test_fetch_location_info_success_capabilities(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                     man_capabilities=[4,9,7],
                                                     opt_capabilities=[5,6])

    def test_fetch_location_info_success_man_capabilities(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                     man_capabilities=[4,9,7])

    def test_fetch_location_info_success_opt_capabilities(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS,
                                                     opt_capabilities=[4,9,7])

    def test_fetch_location_info_success_no_data(self):
        self.common_test_fetch_location_info_success(result_code=resultcodes.DIAMETER_SUCCESS)

    def test_fetch_location_info_success_unreg(self):
        self.common_test_fetch_location_info_success(experimental_result_code=resultcodes.DIAMETER_UNREGISTERED_SERVICE)

    def test_fetch_location_info_no_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_location_info("pub", ORIGINATING, AUTH_TYPES["CAPAB"]),
                             expected_retval=matchers.MatchesNone())

    def test_fetch_location_info_user_unknown_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_location_info("pub", ORIGINATING, AUTH_TYPES["CAPAB"]),
                             experimental_result_code=resultcodes.DIAMETER_ERROR_USER_UNKNOWN,
                             expected_exception=UserNotIdentifiable)

    def test_fetch_location_info_no_identity_registered_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_location_info("pub", ORIGINATING, AUTH_TYPES["CAPAB"]),
                             experimental_result_code=resultcodes.DIAMETER_ERROR_IDENTITY_NOT_REGISTERED,
                             expected_exception=UserNotIdentifiable)

    def test_fetch_location_info_overload_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_location_info("pub", ORIGINATING, AUTH_TYPES["CAPAB"]),
                             result_code=resultcodes.DIAMETER_TOO_BUSY,
                             expected_exception=HSSOverloaded,
                             expected_count=1)

    def test_fetch_location_info_other_error_code(self):
        self.common_test_hss(lambda: self.peer_listener.fetch_location_info("pub", ORIGINATING, AUTH_TYPES["CAPAB"]),
                             result_code=3005,
                             expected_retval=matchers.MatchesNone())

    def common_test_hss(self,
                        function,
                        first_avp=None,
                        result_code=None,
                        experimental_result_code=None,
                        expected_exception=None,
                        expected_retval=matchers.MatchesAnything(),
                        expected_count=0):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = function()
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Now mimic an error returning a value from the HSS
        mock_answer = mock.MagicMock()
        self.cx.findFirstAVP.return_value = first_avp
        # Set the right error code to the expected response
        err_code = mock.MagicMock()
        if result_code:
            err_code.return_value = result_code
            self.peer_listener.get_diameter_result_code = err_code
        elif experimental_result_code:
            err_code.return_value = experimental_result_code
            self.peer_listener.get_diameter_exp_result_code = err_code

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

        # The penalty counter should be at the expected count
        self.assertEquals(penaltycounter.get_hss_penalty_count(), expected_count)

    def common_test_fetch_user_auth_success(self,
                                            result_code=None,
                                            experimental_result_code=None,
                                            scscf=None,
                                            man_capabilities=None,
                                            opt_capabilities=None):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_user_auth("priv", "pub", "Visited 1 Network", 1)
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "User-Authorization", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'Public-Identity': 'pub'},
                           {'Visited-Network-Identifier': 'Visited 1 Network'},
                           {'User-Authorization-Type': 1},
                           {'User-Name': 'priv'}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Capabilities should default to [] but Python doesn't like defaulting to a list
        # in a function definition so do it here.
        man_capabilities = [] if man_capabilities is None else man_capabilities
        opt_capabilities = [] if opt_capabilities is None else opt_capabilities

        self.common_server_mock_resp(result_code,
                                     experimental_result_code,
                                     scscf,
                                     man_capabilities,
                                     opt_capabilities)
        result_code = experimental_result_code if result_code is None else result_code
        self.common_server_check_return_value(deferred,
                                              inner_deferred,
                                              result_code,
                                              scscf,
                                              man_capabilities,
                                              opt_capabilities)

    def common_test_fetch_location_info_success(self,
                                                result_code=None,
                                                experimental_result_code=None,
                                                scscf=None,
                                                man_capabilities=None,
                                                opt_capabilities=None):
        mock_req = self.MockRequest()
        self.cx.getCommandRequest.return_value = mock_req
        deferred = self.peer_listener.fetch_location_info("pub", None, None)
        self.cx.getCommandRequest.assert_called_once_with(self.peer.stack, "Location-Info", True)
        self.assertEquals(mock_req.avps,
                          [{'Session-Id': 'hs.example.com;1234;1'},
                           {'Auth-Session-State': 1},
                           {'Destination-Realm': 'peer-realm'},
                           {'Destination-Host': 'peer-host'},
                           {'Public-Identity': 'pub'}])
        self.peer.stack.sendByPeer.assert_called_once_with(self.peer, mock_req)
        inner_deferred = self.app.add_pending_response.call_args[0][1]
        # Capabilities should default to [] but Python doesn't like defaulting to a list
        # in a function definition so do it here.
        man_capabilities = [] if man_capabilities is None else man_capabilities
        opt_capabilities = [] if opt_capabilities is None else opt_capabilities
        self.common_server_mock_resp(result_code,
                                     experimental_result_code,
                                     scscf,
                                     man_capabilities,
                                     opt_capabilities)
        result_code = experimental_result_code if result_code is None else result_code
        self.common_server_check_return_value(deferred,
                                              inner_deferred,
                                              result_code,
                                              scscf,
                                              man_capabilities,
                                              opt_capabilities)

    def common_server_mock_resp(self,
                                result_code,
                                experimental_result_code,
                                scscf,
                                man_capabilities,
                                opt_capabilities):
        # Mock everything we need for a response from the HSS for a UAR or LIR. The inputs
        # to this function determine whether we return a server name or server capabilities.
        # Start with the result_codes.
        self.peer_listener.get_diameter_result_code = mock.MagicMock(return_value=result_code)
        self.peer_listener.get_diameter_exp_result_code = mock.MagicMock(return_value=experimental_result_code)
        # Now add the server name or server capabilities
        if scscf:
            self.cx.findFirstAVP.return_value = mock.MagicMock()
            self.cx.findFirstAVP.return_value.getOctetString.return_value = scscf
        else:
            mock_capabilities = mock.MagicMock()
            self.cx.findFirstAVP = mock.MagicMock(side_effect=(None, mock_capabilities))
            mock_man_capabilities = []
            for capability in man_capabilities:
                mock_man_capabilities.append(mock.MagicMock())
                mock_man_capabilities[-1].getInteger32.return_value = capability
            mock_opt_capabilities = []
            for capability in opt_capabilities:
                mock_opt_capabilities.append(mock.MagicMock())
                mock_opt_capabilities[-1].getInteger32.return_value = capability
            self.cx.findAVP = mock.MagicMock(side_effect=(mock_man_capabilities, mock_opt_capabilities))
            self.cx.findAVP = mock.MagicMock(side_effect=(mock_man_capabilities, mock_opt_capabilities))

    def common_server_check_return_value(self,
                                         deferred,
                                         inner_deferred,
                                         result_code,
                                         scscf,
                                         man_capabilities,
                                         opt_capabilities):
        # Check we're returning the correct JSON for a UAR or LIR, and check the correct
        # functions are being called.
        mock_answer = mock.MagicMock()
        expected_return_value = {}
        expected_return_value["result-code"] = result_code
        self.cx.findFirstAVP.assert_has_calls(mock_answer, "Server-Name")
        if scscf:
            expected_return_value["scscf"] = scscf
        else:
            expected_return_value["mandatory-capabilities"] = man_capabilities
            expected_return_value["optional-capabilities"] = opt_capabilities
            self.cx.findFirstAVP.assert_has_calls(mock_answer, "Server-Capabilities")
            self.cx.findAVP.assert_has_calls(mock_answer, "Mandatory-Capability")
            self.cx.findAVP.assert_has_calls(mock_answer, "Optional-Capability")

        deferred_callback = mock.MagicMock()
        deferred.addCallback(deferred_callback)
        inner_deferred.callback(mock_answer)
        self.assertEquals(deferred_callback.call_args[0][0], expected_return_value)

    def test_disconnected(self):
        self.assertEquals(self.peer_listener.peer, self.peer)
        self.peer_listener.disconnected(mock.MagicMock())
        self.assertEquals(self.peer_listener.peer.alive, False)

