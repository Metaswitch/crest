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

from mock import ANY, call
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
        self.mock_cass2 = mock.MagicMock()
        self.handler.cass = self.mock_cass


    def test_public_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "priv")

    def test_get_no_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
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
        self.request.body = ""
        self.handler.get("priv")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["pub"]})

    def test_get_many_results(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.get("priv")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub2', value='pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["pub", "pub2"]})

    def test_get_wrong_parms1(self):
        self.request.body = ""
        get_deferred = self.handler.get("priv", "pub")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_wrong_parms1(self):
        self.request.body = ""
        post_deferred = self.handler.post("priv", "pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_add_first_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'pub'

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub',
                                                         finish='pub')

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv')

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback([])


        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2 x insert

        self.mock_cass2.insert.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub', value='pub')
        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.insert.return_value.callback(mock.MagicMock())

        self.mock_cass.insert.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv', value='priv')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["pub"]})


    def test_post_exists(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'pub'

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub',
                                                         finish='pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback(result_list)


        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["pub"]})

    def test_post_update_add_subsequent_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'pub2'

        self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub2',
                                                         finish='pub2')

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback(result_list)


        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub2')

        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2 x insert

        self.mock_cass2.insert.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub2', value='pub2')
        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.insert.return_value.callback(mock.MagicMock())

        self.mock_cass.insert.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE, key='pub2', column='priv', value='priv')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub2', value='pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"private_id": "priv", "public_ids": ["pub", "pub2"]})


    def test_post_update_add_entry_fails_limit_hit(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'pub2'

        post_deferred = self.handler.post("priv")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub2',
                                                         finish='pub2')


        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv')

        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub2', value='pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub3', value='pub3', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub4', value='pub4', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub5', value='pub5', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback(result_list)

        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 400: Bad Request')

    def test_post_missing_body(self):
        self.request.body = ""
        post_deferred = self.handler.post("priv")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_delete_specific_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.delete("priv", "pub")
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_delete_wildcard_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.delete("priv")

        # Expect a call to query the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)


    def test_delete_wildcard_nonexistent(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        get_deferred = self.handler.delete("priv")

        # Expect a call to query the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv')
        self.mock_cass.get_slice.return_value.callback([])

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)





#############################################################################################

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
        self.mock_cass2 = mock.MagicMock()
        self.handler.cass = self.mock_cass

    def test_private_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "pub")

    def test_get_no_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        get_deferred = self.handler.get("pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        self.mock_cass.get_slice.return_value.callback([])
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_get_one_result(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.get("pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass.get_slice.return_value.callback(result_list)
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "pub", "private_ids": ["priv"]})

    def test_get_many_results(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.get("pub")
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
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
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "pub", "private_ids": ["priv", "priv2"]})

    def test_get_wrong_parms1(self):
        self.request.body = ""
        get_deferred = self.handler.get("pub", "priv")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_post_wrong_parms1(self):
        self.request.body = ""
        post_deferred = self.handler.post("pub", "priv")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')


    def test_post_add_first_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'priv'

        self.handler.post("pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub',
                                                         finish='pub')

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv')

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback([])


        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2 x insert

        self.mock_cass2.insert.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub', value='pub')
        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.insert.return_value.callback(mock.MagicMock())

        self.mock_cass.insert.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv', value='priv')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "pub", "private_ids": ["priv"]})

    def test_post_failed_2nd_insert(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'priv'

        post_deferred = self.handler.post("pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub',
                                                         finish='pub')

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv')

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback([])


        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2 x insert

        self.mock_cass2.insert.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub', value='pub')
        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.insert.return_value.callback(mock.MagicMock())

        self.mock_cass.insert.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv', value='priv')

        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.remove.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2

        # the key point... throw an exception from the database.  Doesn't matter what.
        self.mock_cass.insert.return_value.errback(Exception("fail"))

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.remove.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv', column='pub', value='pub')
        self.mock_cass2.remove.return_value.callback(mock.MagicMock())

        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 500: Internal Server Error')

    def test_post_exists(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'priv'

        self.handler.post("pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv',
                                                         start='pub',
                                                         finish='pub')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback(result_list)


        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.OK)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "pub", "private_ids": ["priv"]})

    def test_post_update_add_subsequent_entry(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'priv2'

        self.handler.post("pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv2',
                                                         start='pub',
                                                         finish='pub')

        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv2')

        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback(result_list)


        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')

        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2 x insert

        self.mock_cass2.insert.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv2', column='pub', value='pub')
        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.insert.return_value.callback(mock.MagicMock())

        self.mock_cass.insert.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv2', value='priv2')
        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.insert.return_value.callback(mock.MagicMock())

        # get_slice public IDs, key=priv to get returned data
        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv2', value='priv2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.CREATED)
        self.assertEquals(self.handler.finish.call_args[0][0], {"public_id": "pub", "private_ids": ["priv", "priv2"]})


    def test_post_update_add_entry_fails_limit_hit(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = 'priv2'

        post_deferred = self.handler.post("pub")
        # get_slice to check if it exists
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                         key='priv2',
                                                         start='pub',
                                                         finish='pub')


        # switch to the other mock Cassandra so that subsequent calls don't go straight through.
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback([])

        # 2x get-slice to check for limits

        self.mock_cass2.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE,
                                                          key='priv2')

        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # restore the initial mock cass
        self.mock_cass.reset_mock()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass
        self.mock_cass2.get_slice.return_value.callback(result_list)

        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                          key='pub')

        result_list = [
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv6', value='priv6', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv3', value='priv3', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv4', value='priv4', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None),
            ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv5', value='priv5', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]

        # restore the 2nd mock cass
        self.mock_cass2.reset_mock()
        self.mock_cass2.get_slice.return_value = defer.Deferred()
        self.handler.cass = self.mock_cass2
        self.mock_cass.get_slice.return_value.callback(result_list)

        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 400: Bad Request')

    def test_post_missing_body(self):
        self.request.body = ""
        post_deferred = self.handler.post("pub")
        post_errback = mock.MagicMock()
        post_deferred.addErrback(post_errback)
        self.assertEquals(post_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_delete_specific_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.delete("pub", "priv")
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_delete_wildcard_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        self.handler.delete("pub")

        # Expect a call to query the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='priv', value='priv', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.mock_cass.remove.assert_has_calls([call(column_family=config.PUBLIC_IDS_TABLE, key='priv', column='pub'),
                                                call(column_family=config.PRIVATE_IDS_TABLE, key='pub', column='priv')],
                                               any_order = True)

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)


    def test_delete_wildcard_nonexistent(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = ""
        get_deferred = self.handler.delete("pub")

        # Expect a call to query the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PRIVATE_IDS_TABLE,
                                                         key='pub')
        self.mock_cass.get_slice.return_value.callback([])

        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

