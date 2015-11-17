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

from lxml import etree
from cyclone.web import HTTPError

from metaswitch.crest.api import xsd
from metaswitch.homer import validator

SCHEMA_DIR = os.path.realpath(os.path.join(
    os.getcwd(),
    'homer.root/usr/share/clearwater/homer/schemas'))

# Valid simservs xml

simservs_cb = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:cp="urn:ietf:params:xml:ns:common-policy">
    <incoming-communication-barring active="true">
        <cp:ruleset>
            <cp:rule id="rule1">
                <cp:conditions/>
                <cp:actions>
                    <allow>true</allow>
                </cp:actions>
            </cp:rule>
        </cp:ruleset>
    </incoming-communication-barring>
    <outgoing-communication-barring active="true">
        <cp:ruleset>
            <cp:rule id="rule1">
                <cp:conditions>
                    <international/>
                </cp:conditions>
                <cp:actions>
                    <allow>true</allow>
                </cp:actions>
            </cp:rule>
        </cp:ruleset>
    </outgoing-communication-barring>
</simservs>"""

simservs_cdiv = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:cp="urn:ietf:params:xml:ns:common-policy">
    <communication-diversion active="false">
        <NoReplyTimer>20</NoReplyTimer>
        <cp:ruleset>
            <cp:rule id="rule1">
                <cp:conditions>
                    <busy/>
                </cp:conditions>
                <cp:actions>
                    <forward-to>
                        <target>sip:abc@def.com</target>
                    </forward-to>
                </cp:actions>
            </cp:rule>
        </cp:ruleset>
    </communication-diversion>
</simservs>"""

simservs_fa = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <flexible-alerting-default active="true"/>

    <flexible-alerting-specific active="true">
        <identity>sip:pilot_identity@home1.net</identity>
    </flexible-alerting-specific>
</simservs>"""

simservs_oip = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" >
    <originating-identity-presentation active="true"/>
    <originating-identity-presentation-restriction active="true">
        <default-behaviour>presentation-not-restricted</default-behaviour>
    </originating-identity-presentation-restriction>
</simservs>"""

# Invalid simservs xml

simservs_andy = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" >
    <!-- Strictly speaking, we don't need a XSD validator to verify this,
         however it would be nice to be alerted if ever such a travesty
         was allowed to be written into our database -->
    <andy-is-cool active="true"/>
</simservs>"""


simservs_cb_bad_ns = """<?xml version="1.0" encoding="UTF-8"?>
<simservs
    xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap"
    xmlns:cp="urn:ietf:params:xml:ns:common-policy"
    xmlns:ocp="urn:oma:params:xml:ns:common-policy">
    <incoming-communication-barring active="true">
        <ruleset>
            <rule>
                <conditions/>
                <actions>
                    <allow>true</allow>
                </actions>
            </rule>
        </ruleset>
    </incoming-communication-barring>
    <outgoing-communication-barring active="true">
        <ruleset>
            <rule>
                <conditions/>
                <actions>
                    <allow>true</allow>
                </actions>
            </rule>
        </ruleset>
    </outgoing-communication-barring>
</simservs>"""

simservs_cb_no_rule_id = """<?xml version="1.0" encoding="UTF-8"?>
<simservs
    xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap"
    xmlns:cp="urn:ietf:params:xml:ns:common-policy"
    xmlns:ocp="urn:oma:params:xml:ns:common-policy">
    <incoming-communication-barring active="true">
        <cp:ruleset>
            <cp:rule>
                <cp:conditions/>
                <cp:actions>
                    <allow>true</allow>
                </cp:actions>
            </cp:rule>
        </cp:ruleset>
    </incoming-communication-barring>
</simservs>"""

simservs_cdiv_bad_ns = """<?xml version="1.0" encoding="UTF-8"?>
<simservs xmlns="http://uri.etsi.org/ngn/params/xml/simservs/xcap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <communication-diversion active="false">
        <NoReplyTimer>20</NoReplyTimer>
        <ruleset>
            <rule>
                <conditions>
                    <busy/>
                </conditions>
                <actions>
                    <forward-to>
                        <target>sip:abc@def.com</target>
                    </forward-to>
                </actions>
            </rule>
        </ruleset>
    </communication-diversion>
</simservs>"""

class TestSimservsHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the SimservsHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.factory = mock.MagicMock()

        self.schema_path = os.path.join(SCHEMA_DIR, 'simservs/mmtel.xsd')
        self.handler_class = validator.create_handler(self.schema_path)
        self.handler_class.add_cass_factory("homer", self.factory)

        self.handler = self.handler_class(self.app,
                                          self.request,
                                          factory_name="homer",
                                          table="table",
                                          column="column")

    def tearDown(self):
        pass

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_put_valid(self, passthrough_put, validate):
        self.request.body = "xml_body"
        validate.return_value = True
        self.handler.put("arg1")
        validate.assert_called_once_with("xml_body", self.schema_path)
        passthrough_put.assert_called_once_with(self.handler, "arg1")

    @mock.patch("metaswitch.crest.api.xsd._validate")
    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def test_put_invalid(self, passthrough_put, validate):
        self.request.body = "dodgy_xml_body"
        validate.side_effect = etree.XMLSyntaxError("XML Error", None, None, None)
        self.assertRaisesRegexp(HTTPError, "HTTP 400: Bad Request \(XML Error\)",
                                self.handler.put, "arg1")
        validate.assert_called_once_with("dodgy_xml_body", self.schema_path)

class TestSimservsFunctional(unittest.TestCase):
    """
    Functional tests for testing the simservs xml validation
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.schema_path = os.path.join(SCHEMA_DIR, 'simservs/mmtel.xsd')

    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def assert_valid_simservs(self, xml_doc, passthrough_put):
        result = xsd._validate(xml_doc, self.schema_path)
        self.assertTrue(result)

    def test_simservs_cb(self):
        self.assert_valid_simservs(simservs_cb)

    def test_simservs_cdiv(self):
        self.assert_valid_simservs(simservs_cdiv)

    def test_simservs_fa(self):
        self.assert_valid_simservs(simservs_fa)

    def test_simservs_oip(self):
        self.assert_valid_simservs(simservs_oip)

    @mock.patch("metaswitch.crest.api.passthrough.PassthroughHandler.put")
    def assert_invalid_simservs(self, xml_doc, passthrough_put):
        self.assertRaises(etree.XMLSyntaxError,
                          xsd._validate,
                          xml_doc, self.schema_path)

    def test_simservs_andy_invalid(self):
        self.assert_invalid_simservs(simservs_andy)

    def test_simservs_cb_bad_ns(self):
        self.assert_invalid_simservs(simservs_cb_bad_ns)

    def test_simservs_cb_no_rule_id(self):
        self.assert_invalid_simservs(simservs_cb_no_rule_id)

    def test_simservs_cdiv_bad_ns(self):
        self.assert_invalid_simservs(simservs_cdiv_bad_ns)
