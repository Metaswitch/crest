#!/usr/bin/python

# @file private.py
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2015  Metaswitch Networks Ltd
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

from telephus.cassandra.ttypes import NotFoundException
from metaswitch.homestead_prov.provisioning.handlers import private

class TestPrivateHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the PrivateHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()

        self.handler = private.PrivateHandler(self.app,
                                              self.request)

    def tearDown(self):
        pass

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    def test_put_missing_body(self, send_error):
        self.request.body = ""
        self.handler.put("private_id")
        send_error.assert_called_once_with(400, "Empty body")

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    def test_put_invalid_json(self, send_error):
        self.request.body = "not valid JSON"
        self.handler.put("private_id")
        send_error.assert_called_once_with(400, "Invalid JSON")

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    def test_put_missing_keys(self, send_error):
        self.request.body = "{\"realm\":\"REALM\"}"
        self.handler.put("private_id")
        send_error.assert_called_once_with(400, "Invalid JSON - neither digest_ha1 and plaintext_password present")

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    def test_put_too_many_keys(self, send_error):
        self.request.body = "{\"digest_ha1\":\"DIGEST\", \"plaintext_password\":\"PLAINTEXT_PASSWORD\"}"
        self.handler.put("private_id")
        send_error.assert_called_once_with(400, "Invalid JSON - both digest_ha1 and plaintext_password present")

    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.put_digest")
    def test_put_digest(self, put_digest):
        self.request.body = "{\"digest_ha1\":\"DIGEST\"}"
        self.handler.finish = mock.MagicMock()
        self.handler.put("private_id")
        put_digest.assert_called_once_with("DIGEST", "", "example.com")
        self.assertTrue(self.handler.finish.called)

    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.put_digest")
    def test_put_plaintext_password(self, put_digest):
        self.request.body = "{\"plaintext_password\":\"ptp\", \"realm\": \"realm.com\"}"
        self.handler.finish = mock.MagicMock()
        self.handler.put("private_id")
        put_digest.assert_called_once_with("990e17a100a355169d8a3510b495a685", "ptp", "realm.com")
        self.assertTrue(self.handler.finish.called)

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.get_digest")
    def test_get_missing_subscriber(self, get_digest, send_error):
        get_digest.side_effect = NotFoundException()
        self.handler.get("private_id")
        self.assertTrue(get_digest.called > 0)
        send_error.assert_called_once_with(404)

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_json")
    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.get_digest")
    def test_get_digest(self, get_digest, send_json):
        get_digest.return_value =(("DIGEST", "", "REALM"))
        self.handler.get("private_id")
        send_json.assert_called_once_with({'digest_ha1':'DIGEST', 'realm': 'REALM'})

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_json")
    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.get_digest")
    def test_get_plaintext_password(self, get_digest, send_json):
        get_digest.return_value =(("DIGEST", "PASSWORD", "REALM"))
        self.handler.get("private_id")
        send_json.assert_called_once_with({'digest_ha1':'DIGEST', 'realm': 'REALM', 'plaintext_password': 'PASSWORD'})

    @mock.patch("metaswitch.crest.api.base.BaseHandler.send_error")
    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.delete")
    def test_delete_missing_subscriber(self, delete, send_error):
        delete.side_effect = NotFoundException()
        self.handler.delete("private_id")
        self.assertTrue(delete.called > 0)
        send_error.assert_called_once_with(204)

    @mock.patch("metaswitch.homestead_prov.provisioning.models.PrivateID.delete")
    def test_delete(self, delete):
        self.handler.finish = mock.MagicMock()
        self.handler.delete("private_id")
        self.assertTrue(delete.called > 0)
        self.assertTrue(self.handler.finish.called)

