#!/usr/bin/python

# @file ping.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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
