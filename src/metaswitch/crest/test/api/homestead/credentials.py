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
from telephus.cassandra.ttypes import NotFoundException
from twisted.internet import defer
from twisted.python.failure import Failure

from metaswitch.crest import settings
from metaswitch.crest.api.homestead import credentials
from metaswitch.crest.api.homestead.hss.gateway import HSSNotFound

class TestCredentialsHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the CredentialsHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = credentials.CredentialsHandler(self.app,
                                                      self.request,
                                                      table="table",
                                                      column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass

        self.mock_hss = mock.MagicMock()
        self.handler.application.hss_gateway = self.mock_hss

        # Default to not using HSS, will override in tests that require it
        settings.HSS_IP = ""

    @mock.patch("metaswitch.common.utils.decrypt_password")
    def test_get_mainline(self, decrypt_password):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        decrypt_password.return_value = "dec_pw"
        self.handler.get("priv", "pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        result = mock.MagicMock()
        result.column.value = "enc_pw"
        self.mock_cass.get.return_value.callback(result)
        decrypt_password.assert_called_once_with("enc_pw", settings.PASSWORD_ENCRYPTION_KEY)
        self.assertEquals(self.handler.finish.call_args[0][0], {"digest": "dec_pw"})

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_get_from_hss(self, encrypt_password):
        settings.HSS_IP = "example.com"
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_digest.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        encrypt_password.return_value = "enc_happy_digest"
        self.handler.finish = mock.MagicMock()
        # Get as far as attempting to fetch from Cassandra
        self.handler.get("priv", "pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.mock_hss.get_digest.assert_called_once_with('priv', 'pub')
        # Now, succeed in retreiving from HSS
        self.mock_hss.get_digest.return_value.callback("happy_digest")
        # Finally, the new digest should be put into Cassandra
        encrypt_password.assert_called_once_with("happy_digest", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_happy_digest')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {"digest": "happy_digest"})

    def test_unknown_user(self):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv", "pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_unknown_user_hss(self, encrypt_password):
        settings.HSS_IP = "example.com"
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_digest.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        encrypt_password.return_value = "enc_happy_digest"
        self.handler.finish = mock.MagicMock()
        # Get as far as attempting to fetch from Cassandra
        get_deferred = self.handler.get("priv", "pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.mock_hss.get_digest.assert_called_once_with('priv', 'pub')
        # Now, fail in retreiving from HSS
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_hss.get_digest.return_value.errback(HSSNotFound())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_post_with_digest(self, encrypt_password):
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = '{"digest": "md5_hash"}'
        self.request.headers = {}
        encrypt_password.return_value = "enc_hash"
        self.handler.post("priv", "pub")
        encrypt_password.assert_called_once_with("md5_hash", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_hash')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {})

    @mock.patch("metaswitch.common.utils.md5")
    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_post_with_pw(self, encrypt_password, md5):
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = '{"password": "foo"}'
        self.request.headers = {}
        md5.return_value = "md5_hash"
        encrypt_password.return_value = "enc_hash"
        self.handler.post("priv", "pub")
        md5.assert_called_once_with("priv:%s:foo" % settings.SIP_DIGEST_REALM)
        encrypt_password.assert_called_once_with("md5_hash", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_hash')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {})

    @mock.patch("metaswitch.common.utils.create_secure_human_readable_id")
    @mock.patch("metaswitch.common.utils.md5")
    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_post_without_pw(self, encrypt_password, md5, create_id):
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.request.body = None
        self.request.headers = {}
        md5.return_value = "md5_hash"
        encrypt_password.return_value = "enc_hash"
        create_id.return_value = "pw"
        self.handler.post("priv", "pub")
        md5.assert_called_once_with("priv:%s:pw" % settings.SIP_DIGEST_REALM)
        encrypt_password.assert_called_once_with("md5_hash", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_hash')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {'password': 'pw'})

    def test_delete_mainline(self):
        self.mock_cass.remove.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.handler.delete("priv", "pub")
        self.mock_cass.remove.assert_called_once_with(column='col', column_family='table', key='priv')
        self.mock_cass.remove.return_value.callback(mock.MagicMock())
        self.assertTrue(self.handler.finish.called)
        self.assertEquals(self.handler.get_status(), httplib.NO_CONTENT)

    def test_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "priv", "pub")

    @mock.patch("metaswitch.common.utils.decrypt_password")
    def test_private_get_mainline(self, decrypt_password):
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

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_private_get_from_hss(self, encrypt_password):
        settings.HSS_IP = "example.com"
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_digest.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        encrypt_password.return_value = "enc_happy_digest"
        self.handler.finish = mock.MagicMock()
        # Get as far as attempting to fetch from Cassandra
        self.handler.get("priv")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.mock_hss.get_digest.assert_called_once_with('priv', 'sip:priv')
        # Now, succeed in retreiving from HSS
        self.mock_hss.get_digest.return_value.callback("happy_digest")
        # Finally, the new digest should be put into Cassandra
        encrypt_password.assert_called_once_with("happy_digest", settings.PASSWORD_ENCRYPTION_KEY)
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='priv', value='enc_happy_digest')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], {"digest": "happy_digest"})

    def test_private_unknown_user(self):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("priv")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    @mock.patch("metaswitch.common.utils.encrypt_password")
    def test_private_unknown_user_hss(self, encrypt_password):
        settings.HSS_IP = "example.com"
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_digest.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        encrypt_password.return_value = "enc_happy_digest"
        self.handler.finish = mock.MagicMock()
        # Get as far as attempting to fetch from Cassandra
        get_deferred = self.handler.get("priv")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='priv')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.mock_hss.get_digest.assert_called_once_with('priv', 'sip:priv')
        # Now, fail in retreiving from HSS
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_hss.get_digest.return_value.errback(HSSNotFound())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    def test_private_no_post(self):
        get_deferred = self.handler.post("priv")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_private_no_delete(self):
        get_deferred = self.handler.delete("priv")
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 405: Method Not Allowed')

    def test_private_no_put(self):
        self.assertRaises(HTTPError, self.handler.put, "priv")
