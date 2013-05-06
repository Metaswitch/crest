#!/usr/bin/python

# @file ping.py
#
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by post at
# Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK


import unittest
import mock
from mock import ANY

from metaswitch.crest.api import ping

from metaswitch.crest.test._base import AppTestCase

class TestPingHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the PingHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = ping.PingHandler(self.app, self.request)

    def test_get_mainline(self):
        self.handler.finish = mock.MagicMock()
        self.handler.get()
        self.assertEquals(self.handler.finish.call_args[0][0], "OK")
