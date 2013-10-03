#!/usr/bin/python

# @file passthrough.py
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
import httplib
from mock import ANY
from cyclone.web import HTTPError
from telephus.cassandra.ttypes import NotFoundException
from twisted.internet import defer
from twisted.python.failure import Failure

from metaswitch.crest.api import passthrough

class TestPassthroughHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the PassthroughHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.factory = mock.MagicMock()

        passthrough.PassthroughHandler.add_cass_factory("factory", self.factory)
        self.handler = passthrough.PassthroughHandler(self.app,
                                                      self.request,
                                                      factory_name="factory",
                                                      table="table",
                                                      column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.ha_get = self.mock_cass.get

    def test_get_mainline(self):
        # Create a deferred object that will be used to mock out the yield self.ha_get
        # We will later call the callback on it to advance the execcution of the tested function
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        # Invoke the get function. As we are using inline callbacks this will return once
        # get has yielded (the deferred we created above) - in effect pausing the get
        # function at the point of te yield from our point of view
        self.handler.get("key")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='key')
        # Next we construct the mock result from the database, which we pass as an
        # argument to the deferred's callback function. This will "resume" the get
        # function at the point of the yield, passing throught the value we gave to
        # the callback
        result = mock.MagicMock()
        result.column.value = "db_result"
        self.mock_cass.get.return_value.callback(result)
        # At this stage, the tested get function has returned and we can verify that
        # the all function calls we executed as expected
        self.assertEquals(self.handler.finish.call_args[0][0], "db_result")

    def test_get_not_found(self):
        # As with test_get_mainline above we create a deferred object to mock out the
        # cass.get call
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        # Next we fire the errback callack on the deferred, which defer.inlineCallbacks
        # will convert to an Exception and throw this exception in our get method
        # However, when get throws the HTTPError in response to our passed in exception
        # we cannot simply catch it, because defer.inlineCallbacks will convert this
        # into a Failure object and call the error callback on the get function itself
        # Instead, we hold onto the deferred created when we invoke get and assert
        # that its errback function is called correctly
        get_deferred = self.handler.get("key")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='key')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_put_mainline(self):
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = "exciting_data"
        self.handler.put("key")
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='key', value='exciting_data')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {})

    def test_delete_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.handler.delete("key")
        self.mock_cass.remove.assert_called_once_with(column='col', column_family='table', key='key')
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)
