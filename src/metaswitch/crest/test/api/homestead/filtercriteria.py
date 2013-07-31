#!/usr/bin/python

# @file filtercriteria.py
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
from metaswitch.crest.api.homestead import filtercriteria
from metaswitch.crest.api.homestead.hss.gateway import HSSNotFound

class TestFilterCriteriaHandler(unittest.TestCase):
    """
    Detailed, isolated unit tests of the FilterCriteriaHandler class.
    """
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.app = mock.MagicMock()
        self.request = mock.MagicMock()
        self.handler = filtercriteria.FilterCriteriaHandler(self.app, 
                                                            self.request,
                                                            table="table",
                                                            column="col")
        self.mock_cass = mock.MagicMock()
        self.handler.cass = self.mock_cass
        self.handler.safe_get = self.mock_cass.get
        self.handler.safe_get_slice = self.mock_cass.get_slice
        
        self.mock_hss = mock.MagicMock()
        self.handler.application.hss_gateway = self.mock_hss
        
        # Default to not using HSS, will override in tests that require it
        settings.PASSWORD_ENCRYPTION_KEY = "TOPSECRET"
        settings.HSS_ENABLED = False

    def test_get_mainline(self):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        self.handler.get("pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='pub')
        result = mock.MagicMock()
        result.column.value = "glorious_ifc"
        self.mock_cass.get.return_value.callback(result)
        self.assertEquals(self.handler.finish.call_args[0][0], "glorious_ifc")
    
    @mock.patch("metaswitch.common.utils.sip_public_id_to_private")
    def test_get_from_hss(self, sip_public_id_to_private):
        settings.HSS_ENABLED = True
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_ifc.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        sip_public_id_to_private.return_value = "priv"
        # Get as far as attempting to fetch from Cassandra
        self.handler.get("pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='pub')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        sip_public_id_to_private.assert_called_once_with("pub")
        self.mock_hss.get_ifc.assert_called_once_with('priv', 'pub')
        # Now, succeed in retreiving from HSS
        self.mock_hss.get_ifc.return_value.callback("barmy_ifc")
        # Finally, the new IFC should be put into Cassandra
        self.mock_cass.insert.assert_called_once_with(column='col', column_family='table', key='pub', value='barmy_ifc')
        self.mock_cass.insert.return_value.callback(mock.MagicMock())
        self.assertEquals(self.handler.finish.call_args[0][0], "barmy_ifc")
    
    def test_unknown_user(self):
        self.mock_cass.get.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        get_deferred = self.handler.get("pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='pub')
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_cass.get.return_value.errback(NotFoundException())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')

    @mock.patch("metaswitch.common.utils.sip_public_id_to_private")
    def test_unknown_user_hss(self, sip_public_id_to_private):
        settings.HSS_ENABLED = True
        self.mock_cass.get.return_value = defer.Deferred()
        self.mock_hss.get_ifc.return_value = defer.Deferred()
        self.mock_cass.insert.return_value = defer.Deferred()
        self.handler.finish = mock.MagicMock()
        sip_public_id_to_private.return_value = "priv"
        # Get as far as attempting to fetch from Cassandra
        get_deferred = self.handler.get("pub")
        self.mock_cass.get.assert_called_once_with(column='col', column_family='table', key='pub')
        # Next, fail the GET from Cassandra
        self.mock_cass.get.return_value.errback(NotFoundException())
        sip_public_id_to_private.assert_called_once_with("pub")
        self.mock_hss.get_ifc.assert_called_once_with('priv', 'pub')
        # Now, fail in retreiving from HSS
        get_errback = mock.MagicMock()
        get_deferred.addErrback(get_errback)
        self.mock_hss.get_ifc.return_value.errback(HSSNotFound())
        self.assertEquals(get_errback.call_args[0][0].getErrorMessage(), 'HTTP 404: Not Found')
    
