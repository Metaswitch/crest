#!/usr/bin/python

# @file simservs.py
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


import os
import unittest
import mock
from mock import ANY

from lxml import etree
from twisted.internet import defer
from cyclone.web import HTTPError

from metaswitch.crest.api import xsd
from metaswitch.crest.api.homer import simservs
from metaswitch.crest.test._base import AppTestCase

XML_DIR_NAME = "test_xml"
XML_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), XML_DIR_NAME)

class TestSimservsHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the SimservsHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.factory = mock.MagicMock()

        simservs.SimservsHandler.add_cass_factory("homer", self.factory)
        self.handler = simservs.SimservsHandler(self.app,
                                                self.request,
                                                factory_name="homer",
                                                table="table",
                                                column="column")

    def tearDown(self):
        simservs._parsers = {}

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_put_valid(self, passthrough_put, validate):
        self.request.body = "xml_body"
        validate.return_value = True
        self.handler.put("arg1")
        validate.assert_called_once_with("xml_body", simservs.SCHEMA_PATH)
        passthrough_put.assert_called_once_with(self.handler, "arg1")

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_put_invalid(self, passthrough_put, validate):
        self.request.body = "dodgy_xml_body"
        validate.side_effect = etree.XMLSyntaxError("XML Error", None, None, None)
        self.assertRaisesRegexp(HTTPError, "HTTP 400: Bad Request \(XML Error\)",
                                self.handler.put, "arg1")
        validate.assert_called_once_with("dodgy_xml_body", simservs.SCHEMA_PATH)

class TestSimservsFunctional(unittest.TestCase):
    """
    Functional tests for testing the simservs xml validation
    """
    def setUp(self):
        unittest.TestCase.setUp(self)

    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def assert_valid_simservs(self, file_name, passthrough_put):
        with open(os.path.join(XML_DIR, file_name)) as f:
            xml_doc = f.read()
        result = xsd._validate(xml_doc, simservs.SCHEMA_PATH)
        self.assertTrue(result)

    def test_simservs_cb(self):
        self.assert_valid_simservs("simservs_cb.xml")

    def test_simservs_cdiv(self):
        self.assert_valid_simservs("simservs_cdiv.xml")

    def test_simservs_fa(self):
        self.assert_valid_simservs("simservs_fa.xml")

    def test_simservs_oip(self):
        self.assert_valid_simservs("simservs_oip.xml")

    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def assert_invalid_simservs(self, file_name, passthrough_put):
        with open(os.path.join(XML_DIR, file_name)) as f:
            xml_doc = f.read()
        self.assertRaises(etree.XMLSyntaxError,
                          xsd._validate,
                          xml_doc, simservs.SCHEMA_PATH)

    def test_simservs_andy_invalid(self):
        self.assert_invalid_simservs("simservs_andy.xml")

    def test_simservs_cb_bad_ns(self):
        self.assert_invalid_simservs("simservs_cb_bad_ns.xml")

    def test_simservs_cb_no_rule_id(self):
        self.assert_invalid_simservs("simservs_cb_no_rule_id.xml")

    def test_simservs_cdiv_bad_ns(self):
        self.assert_invalid_simservs("simservs_cdiv_bad_ns.xml")
