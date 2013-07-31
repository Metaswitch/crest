#!/usr/bin/python

# @file associatedURIs.py
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

from mock import ANY, call, DEFAULT
from cyclone.web import HTTPError
from telephus.cassandra.ttypes import NotFoundException, Column, ColumnOrSuperColumn
from twisted.internet import defer
from twisted.python.failure import Failure

from metaswitch.crest import settings
from metaswitch.crest.api.homestead import associatedURIs
from metaswitch.crest.api.homestead import config

class TestAssociatedPublicHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the associatedPublicHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = associatedURIs.AssociatedPublicHandler(self.app,
                                                              self.request,
                                                              table=config.PUBLIC_IDS_TABLE,
                                                              column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.safe_get = self.mock_cass.get
        self.handler.safe_get_slice = self.mock_cass.get_slice

    def test_public_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "priv")

    def test_get_no_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        get_deferred = self.handler.get("priv")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        self.mock_cass.get_slice.return_value.callback([])
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_get_one_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("priv")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["sip:pub"]})

    def test_get_many_results(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("priv")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub2', value='sip:pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["sip:pub", "sip:pub2"]})

    def test_get_wrong_parms1(self):
        self.request.arguments = {}
        get_deferred = self.handler.get("priv", "sip:pub")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_wrong_parms1(self):
        self.request.arguments = {}
        post_deferred = self.handler.post("priv", "sip:pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_add_first_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'public_id': 'sip:pub'}

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()

        # prepare for the 2x get-slice calls to check for limits
        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv'):
                return []
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub'):
                return []
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice
        self.mock_cass.insert.return_value = defer.Deferred()

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices, and then
                         # the two inserts

        # Restore the get_slice mock in in advance of the final call on it.
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get_slice.side_effect = None

        self.mock_cass.insert.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub', value='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv', value='priv')],
                                               any_order = True)

        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["sip:pub"]})

    def test_post_exists(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'public_id': 'sip:pub' }

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        rv.callback(result_list)

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["sip:pub"]})

    def test_post_update_add_subsequent_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'public_id': 'sip:pub2' }

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub2',
                                                         finish='sip:pub2')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()

        # Prepare for the 2x get-slice calls to check for limits
        # return the first call with data, the 2nd without
        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv'):
                return (
                    [ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None)])
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub2'):
                return []
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice
        self.mock_cass.insert.return_value = defer.Deferred()

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices, and then
                         # the two inserts

        # Restore the get_slice mockin in advance of the final call on it.
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get_slice.side_effect = None

        self.mock_cass.insert.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub2', value='sip:pub2'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub2', column='priv', value='priv')],
                                               any_order = True)

        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')

        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub2', value='sip:pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["sip:pub", "sip:pub2"]})

    def test_post_update_add_entry_fails_limit_hit(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'public_id': 'sip:pub2' }

        post_deferred = self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub2',
                                                         finish='sip:pub2')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()

        # Prepare for the 2x get-slice calls to check for limits
        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv'):
                return (
                   [ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None),
                    ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub2', value='sip:pub2', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None),
                    ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub3', value='sip:pub3', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None),
                    ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub4', value='sip:pub4', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None),
                    ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub5', value='sip:pub5', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None)])
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub2'):
                return []
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices

        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 400: Bad Request')

    def test_post_missing_body(self):
        self.request.arguments = {}
        post_deferred = self.handler.post("priv")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_delete_specific_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.delete("priv", "sip:pub")
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_delete_wildcard_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.delete("priv")

        # Expect a call to query the set of IDs to delete
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)


    def test_delete_wildcard_nonexistent(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        get_deferred = self.handler.delete("priv")

        # Expect a call to query the set of IDs to delete
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        self.mock_cass.get_slice.return_value.callback([])

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)


class TestAssociatedPrivateHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the associatedPrivateHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = associatedURIs.AssociatedPrivateHandler(self.app,
                                                               self.request,
                                                               table=config.PRIVATE_IDS_TABLE,
                                                               column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.safe_get = self.mock_cass.get
        self.handler.safe_get_slice = self.mock_cass.get_slice

    def test_private_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "sip:pub")

    def test_get_no_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        get_deferred = self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        self.mock_cass.get_slice.return_value.callback([])
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_get_one_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "sip:pub", "private_ids": ["priv"]})

    def test_get_many_results(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv2', value='priv2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "sip:pub", "private_ids": ["priv", "priv2"]})

    def test_get_wrong_parms1(self):
        self.request.arguments = {}
        get_deferred = self.handler.get("sip:pub", "priv")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_wrong_parms1(self):
        self.request.arguments = {}
        post_deferred = self.handler.post("sip:pub", "priv")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_add_first_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'private_id': 'priv' }

        self.handler.post("sip:pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()

        # Prepare for 2x get-slice calls to check for limits
        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv'):
                return []
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub'):
                return []
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice
        self.mock_cass.insert.return_value = defer.Deferred()

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices, and then
                         # the two inserts

        # Restore the get_slice mock in in advance of the final call on it.
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get_slice.side_effect = None

        self.mock_cass.insert.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub', value='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv', value='priv')],
                                               any_order = True)

        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "sip:pub", "private_ids": ["priv"]})

    def test_post_failed_2nd_insert(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'private_id': 'priv' }

        post_deferred = self.handler.post("sip:pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()

        # Prepare for 2x get-slice to check for limits
        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv'):
                return []
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub'):
                self.mock_cass.get_slice.return_value = defer.Deferred()
                return []
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice

        # Prepare for 2x insert calls, one of which we will throw an exception on
        def side_effect_insert (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv' and
                                   column == 'sip:pub' and value == 'sip:pub'):
                return mock.MagicMock()
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub' and
                                         column == 'priv' and value == 'priv'):
                # the key point... throw an exception from the database.  Doesn't matter what.
                raise Exception("fail")
            else:
                raise Exception('FAIL')

        self.mock_cass.insert.side_effect = side_effect_insert

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices, and then
                         # the two inserts

        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub', value='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv', value='priv')])
        self.mock_cass.remove.return_value.callback(mock.MagicMock())

        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 500: Internal Server Error')

    def test_post_exists(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'private_id': 'priv' }

        self.handler.post("sip:pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        rv.callback(result_list)

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "sip:pub", "private_ids": ["priv"]})

    def test_post_update_add_entry_fails_limit_hit(self):
        # This is correct for the case where each public ID can only be
        # associated with one private ID.
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = { 'private_id': 'priv2' }

        post_deferred = self.handler.post("sip:pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv2',
                                                         start='sip:pub',
                                                         finish='sip:pub')

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()

        # Prepare for 2x get-slice calls to check for limits

        def side_effect_slice (column_family, key):
            if (column_family == config.PUBLIC_IDS_TABLE and key == 'priv2'):
                return (
                   [ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None)])
            elif (column_family == config.PRIVATE_IDS_TABLE and key == 'sip:pub'):
                return(
                   [ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
                    name='priv', value='priv', ttl=None), counter_super_column=None,
                    super_column=None, counter_column=None)])
            else:
                raise Exception('FAIL')

        self.mock_cass.get_slice.side_effect = side_effect_slice

        rv.callback([])  # The callback on the original get_slice
                         # This will trigger the 2 get_slices

        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 400: Bad Request')

    def test_post_missing_body(self):
        self.request.arguments = {}
        post_deferred = self.handler.post("sip:pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_delete_specific_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.delete("sip:pub", "priv")
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_delete_wildcard_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.delete("sip:pub")

        # Expect a call to query the set of IDs to delete
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='sip:pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='sip:pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_delete_wildcard_nonexistent(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        get_deferred = self.handler.delete("sip:pub")

        # Expect a call to query the set of IDs to delete
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        self.mock_cass.get_slice.return_value.callback([])

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

class TestAssociatedPublicByPublicHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the associatedPublicByPublicHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = associatedURIs.AssociatedPublicByPublicHandler(self.app,
                                                               self.request,
                                                               table=config.PRIVATE_IDS_TABLE,
                                                               column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.safe_get = self.mock_cass.get
        self.handler.safe_get_slice = self.mock_cass.get_slice

    def test_pubbypub_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "sip:pub")

    def test_pubbypub_no_post(self):
        self.assertRaises(HTTPError, self.handler.post, "sip:pub")

    def test_pubbypub_no_delete(self):
        self.assertRaises(HTTPError, self.handler.delete, "sip:pub")

    def test_get_no_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        get_deferred = self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        self.mock_cass.get_slice.return_value.callback([])
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_get_one_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # set the 2nd mock cass
        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        rv.callback(result_list)

        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                        key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_ids": ["sip:pub"]})

    def test_get_many_results(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.arguments = {}
        self.handler.get("sip:pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='sip:pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        rv = self.mock_cass.get_slice.return_value
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        rv.callback(result_list)

        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub', value='sip:pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub2', value='sip:pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='sip:pub3', value='sip:pub3', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_ids": ["sip:pub", "sip:pub2", "sip:pub3"]})

