#!/usr/bin/python

# @file private.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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

