#!/usr/bin/python

# @file ping.py
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

import unittest
import mock
from twisted.internet.defer import fail
import telephus.protocol

from metaswitch.crest.api import ping


class TestPingHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the PingHandler class.
    """
    # It would be good to FV the failure case where the get request
    # hangs waiting on Cassandra to respond, but that's hard to
    # simulate reliably here.
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = ping.PingHandler(self.app, self.request)

    @mock.patch('twisted.internet.defer.DeferredList',
                autospec=True)
    @mock.patch('metaswitch.crest.api.passthrough.PassthroughHandler',
                autospec=True)
    @mock.patch('telephus.protocol.ManagedCassandraClientFactory',
                autospec=True)
    def test_get_mainline(self,
                          mock_client_factory,
                          mock_passthrough_handler,
                          mock_deferred_list):
        """Test that the ping runs to completion in the mainline."""

        # Make sure there is at least one (fake) connection to Cassandra, to
        # exercise the main logic, and check that only real methods are
        # called.
        ping.PingHandler.register_cass_factory(telephus.protocol.ManagedCassandraClientFactory())
        mock_deferred_list.return_value = fail(Exception())

        # Insert a mock so that we can extract the value that finish
        # was called with.
        with mock.patch.object(self.handler, 'finish') as mock_finish:
            self.handler.get()

        self.assertEquals(mock_finish.call_args[0][0], "OK")
