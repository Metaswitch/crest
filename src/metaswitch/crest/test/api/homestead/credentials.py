#!/usr/bin/python

# @file credentials.py
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

from mock import ANY
from cyclone.web import HTTPError
from telephus.cassandra.ttypes import NotFoundException, Column, ColumnOrSuperColumn
from twisted.internet import defer
from twisted.python.failure import Failure

from metaswitch.crest import settings
from metaswitch.crest.api.homestead import credentials
from metaswitch.crest.api.homestead.hss.gateway import HSSNotFound
from metaswitch.crest.api.homestead import config

class TestPrivateCredentialsHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the PrivateCredentialsHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = credentials.PrivateCredentialsHandler(self.app,
                                                             self.request,
                                                             table="table",
                                                             column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.reliable_get = self.mock_cass.get
        self.handler.reliable_get_slice = self.mock_cass.get_slice

        self.mock_hss = mock.MagicMock()
        self.handler.application.hss_gateway = self.mock_hss

        # Default to not using HSS, will override in tests that require it
        settings.PASSWORD_ENCRYPTION_KEY = "TOPSECRET"
        settings.HSS_ENABLED = False

    @mock.patch("metaswitch.common.utils.decrypt_password")
    def test_get_mainline(self, decrypt_password):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        decrypt_password.return_value = "dec_pw"
        self.handler.get("priv")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        result = mock.MagicMock()
        result.column.value = "enc_pw"
        self.mock_cass.get.return_value.callback(result)
        decrypt_password.assert_called_once_with("enc_pw", settings.PASSWORD_ENCRYPTION_KEY)
        self.assertEquals(self.handler.finish.call_args[0][0], {"digest": "dec_pw"})

    def test_unknown_user(self):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_put_with_digest(self, encrypt_password):
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = '{"digest": "md5_hash"}'
        self.request.headers = {}
        encrypt_password.return_value = "enc_hash"
        self.handler.put("priv")
        encrypt_password.assert_called_once_with("md5_hash", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_hash')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {})

    def test_delete_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.handler.delete("priv")
        self.mock_cass.remove.assert_called_once_with(column='col', column_family='table', key='priv')
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_no_post(self):
        self.assertRaises(HTTPError, self.handler.post, "priv")



class TestAssocCredentialsHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the AssociatedCredentialsHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = credentials.AssociatedCredentialsHandler(self.app,
                                                                self.request,
                                                                table="table",
                                                                column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.reliable_get = self.mock_cass.get
        self.handler.reliable_get_slice = self.mock_cass.get_slice

        self.mock_hss = mock.MagicMock()
        self.handler.application.hss_gateway = self.mock_hss

        # Default to not using HSS, will override in tests that require it
        settings.HSS_ENABLED = False

    def test_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "priv", "pub")

    def test_no_post(self):
        self.assertRaises(HTTPError, self.handler.post, "priv", "pub")

    def test_no_delete(self):
        self.assertRaises(HTTPError, self.handler.delete, "priv", "pub")

    @mock.patch("metaswitch.common.utils.decrypt_password")
    def test_get_mainline(self, decrypt_password):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        decrypt_password.return_value = "dec_pw"

        # Make the call
        self.handler.get("priv", "pub")

        # Expect a call to validate the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', start='pub', finish='pub')
        result = mock.MagicMock()
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        # Now the database query to retrieve the digest
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        result = mock.MagicMock()
        result.column.value = "enc_pw"
        self.mock_cass.get.return_value.callback(result)
        decrypt_password.assert_called_once_with("enc_pw", settings.PASSWORD_ENCRYPTION_KEY)
        self.assertEquals(self.handler.finish.call_args[0][0], {"digest": "dec_pw"})

    def test_user_no_digest(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv", "pub")

        # Expect a call to validate the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', start='pub', finish='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub', value='pub', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_user_wrong_association(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv", "pub")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)

        # Expect a call to validate the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', start='pub', finish='pub')
        result_list = [
             ColumnOrSuperColumn(column=Column(timestamp=1371131096949743,
            name='pub2', value='pub2', ttl=None), counter_super_column=None,
            super_column=None, counter_column=None)]
        self.mock_cass.get_slice.return_value.callback(result_list)

        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_unassociated_user(self):
        self.mock_cass.get_slice.return_value = defer.Deferred()
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv", "pub")

        # Expect a call to validate the pub/priv
        self.mock_cass.get_slice.assert_called_once_with(column_family=config.PUBLIC_IDS_TABLE, key='priv', start='pub', finish='pub')

        self.mock_cass.get_slice.return_value.callback([])

        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

