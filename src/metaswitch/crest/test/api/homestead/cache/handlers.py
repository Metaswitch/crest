#!/usr/bin/python

# @file cache.py
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

import mock
import unittest
import time

from metaswitch.crest.api.homestead.cache.handlers import DigestHandler, AuthVectorHandler
from metaswitch.crest.api.homestead.auth_vectors import DigestAuthVector, AKAAuthVector

class TestDigestHandler(unittest.TestCase):
    def setUp(self):
        self.handler = DigestHandler(mock.MagicMock(), mock.MagicMock())
        self.handler._start = time.time()
        self.handler.application.cache.get_av = mock.MagicMock()
        self.handler.finish = mock.MagicMock()
        self.handler.send_error = mock.MagicMock()

    def test_cache_success_output(self):
        self.handler.application.cache.get_av.return_value = DigestAuthVector("ha1_test", None, None)
        self.handler.get("private_id")
        self.handler.finish.assert_called_once_with({"digest_ha1": "ha1_test"})

    def test_backend_success_output(self):
        self.handler.application.cache.get_av.return_value = None
        self.handler.application.backend.get_av.return_value = DigestAuthVector("ha1_test", None, None)
        self.handler.get("private_id")
        self.handler.finish.assert_called_once_with({"digest_ha1": "ha1_test"})

    def test_failure_output(self):
        self.handler.application.cache.get_av.return_value = None
        self.handler.application.backend.get_av.return_value = None
        self.handler.get("private_id")
        self.handler.send_error.assert_called_once_with(404)

class TestAuthVectorHandler(unittest.TestCase):
    def setUp(self):
        def digest_arg(param, default):
            if param in self.request_args:
                return self.request_args[param]
            return default

        self.handler = AuthVectorHandler(mock.MagicMock(), mock.MagicMock())
        self.handler.get_argument = mock.MagicMock()

        self.handler.get_argument.side_effect = digest_arg
        self.handler._start = time.time()
        self.handler.application.cache.get_av = mock.MagicMock()
        self.handler.finish = mock.MagicMock()
        self.handler.send_error = mock.MagicMock()

class TestAuthVectorHandlerUnknown(TestAuthVectorHandler):
    def setUp(self):
        TestAuthVectorHandler.setUp(self)
        self.request_args = {"authtype": "Unknown"}

    def test_cache_success_output(self):
        expected = {"digest": {"ha1": "ha1_test", "realm": "default-realm2.com", "qop": "auth-int"}}
        self.handler.application.cache.get_av.return_value = DigestAuthVector("ha1_test", "default-realm2.com", "auth-int")
        self.handler.get("private_id")
        self.handler.finish.assert_called_once_with(expected)

    def test_backend_success_output(self):
        expected = {"digest": {"ha1": "ha1_test", "realm": "default-realm2.com", "qop": "auth-int"}}
        self.handler.application.cache.get_av.return_value = None
        self.handler.application.backend.get_av.return_value = DigestAuthVector("ha1_test", "default-realm2.com", "auth-int")
        self.handler.get("private_id")
        self.handler.finish.assert_called_once_with(expected)

    def test_failure_output(self):
        self.handler.application.cache.get_av.return_value = None
        self.handler.application.backend.get_av.return_value = None
        self.handler.get("private_id")
        self.handler.send_error.assert_called_once_with(404)

class TestAuthVectorHandlerDigest(TestAuthVectorHandlerUnknown):
    def setUp(self):
        TestAuthVectorHandler.setUp(self)
        self.request_args = {"authtype": "SIP-Digest"}

class TestAuthVectorHandlerAKA(TestAuthVectorHandler):
    def setUp(self):
        TestAuthVectorHandler.setUp(self)
        self.request_args = {"authtype": "Digest-AKAv1-MD5"}

    def test_cache_not_used(self):
        self.handler.get("private_id")
        self.assertFalse(self.handler.application.cache.get_av.called)

    def test_failure_output(self):
        self.handler.application.backend.get_av.return_value = None
        self.handler.get("private_id")
        self.handler.send_error.assert_called_once_with(404)

    def test_backend_success_output(self):
        expected = {"aka": {"challenge": "rand", "response": "xres", "cryptkey": "ck", "integritykey": "ik"}}
        self.handler.application.backend.get_av.return_value = AKAAuthVector("rand", "xres", "ck", "ik")
        self.handler.get("private_id")
        self.handler.finish.assert_called_once_with(expected)
