#!/usr/bin/python

# @file backend.py
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

from mock import ANY
from twisted.internet import defer

from metaswitch.crest.api.homestead.backends.hss import HSSBackend

class HSSBackendFixture(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        patcher = mock.patch("metaswitch.crest.api.homestead.backends.hss.backend.HSSGateway")
        self.HSSGateway = patcher.start()
        self.addCleanup(patcher.stop)

class TestHSSBackendInitialization(HSSBackendFixture):
    def test_backend_creates_gateway(self):
        self.cache = mock.MagicMock()
        self.backend = HSSBackend(self.cache)
        self.HSSGateway.assert_called_once_with()

class TestHSSBackend(HSSBackendFixture):
    def setUp(self):
        super(TestHSSBackend, self).setUp()
        self.timestamp = 1234
        self.cache = mock.MagicMock()
        self.cache.generate_timestamp.return_value = self.timestamp

        self.gateway = mock.MagicMock()
        self.HSSGateway.return_value = self.gateway
        self.backend = HSSBackend(self.cache)

    def test_get_digest_nothing_returned(self):
        """When no digest is returned from the HSS that backend returns None and
        does not update the cache"""

        self.gateway.get_digest.return_value = defer.Deferred()
        get_deferred = self.backend.get_digest("priv", "pub")

        self.gateway.get_digest.assert_called_once_with("priv", "pub")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)

        self.gateway.get_digest.return_value.callback(None)
        self.assertEquals(get_callback.call_args[0][0], None)

        # The cache is not updated.
        self.assertFalse(self.cache.method_calls)

    def test_get_digest_something_returned(self):
        """When a digest is returned from the HSS the backend returns it and
        updates the cache"""

        self.gateway.get_digest.return_value = defer.Deferred()
        self.cache.put_digest.return_value = defer.Deferred()
        self.cache.put_associated_public_id.return_value = defer.Deferred()

        get_deferred = self.backend.get_digest("priv", "pub")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)

        self.gateway.get_digest.assert_called_once_with("priv", "pub")
        self.gateway.get_digest.return_value.callback("some_digest")

        self.cache.put_digest.assert_called_once_with("priv",
                                                      "some_digest",
                                                       self.timestamp)
        self.cache.put_digest.return_value.callback(None)

        self.cache.put_associated_public_id.assert_called_once_with(
                                                  "priv", "pub", self.timestamp)
        self.cache.put_associated_public_id.return_value.callback(None)

        self.assertEquals(get_callback.call_args[0][0], "some_digest")

    def test_get_digest_no_public_id(self):
        """If a public is not supplied when trying to get a digest, the backend
        does not query the HSS or update the cache"""

        get_deferred = self.backend.get_digest("priv")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)
        self.assertEquals(get_callback.call_args[0][0], None)

        # We haven't queried the gateway or updated the cache.
        self.assertFalse(self.gateway.method_calls)
        self.assertFalse(self.cache.method_calls)

    def test_get_ims_subscription_nothing_returned(self):
        """When no IMS subscription is returned from the HSS the backend returns
        None and does not update the cache"""

        self.gateway.get_ims_subscription.return_value = defer.Deferred()

        get_deferred = self.backend.get_ims_subscription("pub", "priv")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)

        self.gateway.get_ims_subscription.assert_called_once_with("priv", "pub")
        self.gateway.get_ims_subscription.return_value.callback(None)
        self.assertEquals(get_callback.call_args[0][0], None)

        # The cache is not updated.
        self.assertFalse(self.cache.method_calls)

    def test_get_ims_subscription_xml_returned(self):
        """When an IMS subscription is returned from the HSS it is returned by
        the backend, which also updates the cache"""

        self.gateway.get_ims_subscription.return_value = defer.Deferred()
        self.cache.put_ims_subscription.return_value = defer.Deferred()

        get_deferred = self.backend.get_ims_subscription("pub", "priv")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)

        self.gateway.get_ims_subscription.assert_called_once_with("priv", "pub")
        self.gateway.get_ims_subscription.return_value.callback("xml")

        self.cache.put_ims_subscription.assert_called_once_with(
                                                   "pub", "xml", self.timestamp)
        self.cache.put_ims_subscription.return_value.callback(None)

        self.assertEquals(get_callback.call_args[0][0], "xml")

    def test_get_ims_subscription_no_priv_id(self):
        """When getting an IMS subscription and no private ID is supplied, no
        private ID is passed to the HSS.  The backend returns the result of the
        HSS query"""

        self.gateway.get_ims_subscription.return_value = defer.Deferred()

        get_deferred = self.backend.get_ims_subscription("sip:pub")
        get_callback = mock.MagicMock()
        get_deferred.addCallback(get_callback)

        self.gateway.get_ims_subscription.assert_called_once_with(None, "sip:pub")
        self.gateway.get_ims_subscription.return_value.callback(None)
        self.assertEquals(get_callback.call_args[0][0], None)
