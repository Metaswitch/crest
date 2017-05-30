#!/usr/bin/python

# @file xsd.py
#
# Copyright (C) Metaswitch Networks 2013
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


import os
import unittest
import mock

from lxml import etree
from cyclone.web import HTTPError

from metaswitch.crest.api import xsd

XML_DIR_NAME = "test_xml"
XML_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), XML_DIR_NAME)

class TestXSD(unittest.TestCase):
    """
    Detailed, isolated unit tests of the xsd decorator
    """
    def setUp(self):
        unittest.TestCase.setUp(self)

    def tearDown(self):
        xsd._parsers = {}

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_decorator(self, passthrough_put, validate):
        decorator = xsd.validate("schema_path")
        func = mock.MagicMock()
        decorated = decorator(func)
        self.request = mock.MagicMock()
        self.request.body = "xml_body"
        validate.return_value = True
        decorated(self, "arg1")
        validate.assert_called_once_with("xml_body", "schema_path")
        func.assert_called_once_with(self, "arg1")

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_decorator_error(self, passthrough_put, validate):
        decorator = xsd.validate("schema_path")
        func = mock.MagicMock()
        decorated = decorator(func)
        self.request = mock.MagicMock()
        self.request.body = "dodgy_xml_body"
        validate.side_effect = etree.XMLSyntaxError("XML Error", None, None, None)
        self.assertRaisesRegexp(HTTPError, "HTTP 400: Bad Request \(XML Error\)",
                                decorated,
                                self, "arg1")
        validate.assert_called_once_with("dodgy_xml_body", "schema_path")
        self.assertFalse(func.called)

    @mock.patch("lxml.etree.fromstring")
    @mock.patch("metaswitch.crest.api.xsd._get_parser")
    def test_validate(self, get_parser, fromstring):
        get_parser.return_value = "parser"
        xsd._validate("xml", "schema_name")
        get_parser.assert_called_once_with("schema_name")
        fromstring.assert_called_once_with("xml", "parser")

    @mock.patch("lxml.etree.fromstring")
    @mock.patch("metaswitch.crest.api.xsd._get_parser")
    def test_validate_throw(self, get_parser, fromstring):
        get_parser.return_value = "parser"
        fromstring.side_effect = etree.XMLSyntaxError("XML Error", None, None, None)
        self.assertRaisesRegexp(etree.XMLSyntaxError, "XML Error",
                                xsd._validate,
                                "xml", "schema_name")
        get_parser.assert_called_once_with("schema_name")
        fromstring.assert_called_once_with("xml", "parser")

    @mock.patch("lxml.etree.parse")
    @mock.patch("lxml.etree.XMLSchema")
    @mock.patch("lxml.etree.XMLParser")
    def test_get_parser(self, xml_parser, xml_schema, parse):
        file_name = os.path.realpath(__file__) #Any file will do, as long as it exists, so use ourselves
        xml_parser.return_value = "parser"
        parser = xsd._get_parser(file_name)
        self.assertEquals("parser", parser)
        # Parser should be cached away now, check by changing the returned parser
        xml_parser.return_value = "different_parser"
        parser = xsd._get_parser(file_name)
        self.assertEquals("parser", parser)
