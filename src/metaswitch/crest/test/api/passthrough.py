#!/usr/bin/python

# @file passthrough.py
#
# Copyright (C) Metaswitch Networks 2013
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


import unittest
import mock
import httplib
from telephus.cassandra.ttypes import NotFoundException
from twisted.internet import defer

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
