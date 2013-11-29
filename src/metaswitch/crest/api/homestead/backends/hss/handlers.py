# @file handlers.py
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

import logging
from metaswitch.crest import settings
import time

from cyclone.web import HTTPError
from twisted.internet import defer

from metaswitch.crest.api.base import BaseHandler, hss_latency_accumulator
_log = logging.getLogger("crest.api.homestead.hss")

class HSSApiHandler(BaseHandler):
    def send_error_or_response(self, retval):
        if retval is None:
            self.send_error(500)
        elif isinstance(retval, HTTPError):
            self.send_error(retval.status_code)
        else:
            self.finish(retval)

    @defer.inlineCallbacks
    def getter(self, getter_function, *pos_args, **kwd_args):
        # Track the latency of each request (in usec)
        start_time = time.time()
        retval = yield getter_function(*pos_args, **kwd_args)
        hss_latency_accumulator.accumulate((time.time() - start_time) * 1000000)
        if retval:
            _log.debug("Got result")
            defer.returnValue(retval)
        else:
            _log.debug("No result")

class RegistrationStatusHandler(HSSApiHandler):
    @defer.inlineCallbacks
    def get(self, private_id):
        # auth_type dictionary matching strings defined for URL to enumerated values
        # for User-Authorization AVP defined in RFC 4740.
        auth_types = {"REG" : 0, "DEREG" : 1, "CAPAB" : 2}
        public_id = self.get_argument("impu", default=None)
        visited_network = self.get_argument("visited-network", default=settings.SIP_DIGEST_REALM)
        auth_type_str = self.get_argument("auth_type", default=None)
        if auth_type_str in auth_types.keys():
            auth_type = auth_types[auth_type_str]
        else:
            auth_type = auth_types["REG"]
        retval = yield self.getter(self.application.backend.get_registration_status, private_id, public_id, visited_network, auth_type)
        self.send_error_or_response(retval)

class LocationInformationHandler(HSSApiHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        # Constant to match the enumerated value for Originating-Request AVP in 3GPP 29.229
        ORIGINATING = 0
        # Constant to match the enumerated value for User-Authorization AVP in RFC 4740
        REGISTRATION_AND_CAPABILITIES = 2
        # originating parameter is either set to ORIGINATING or None
        originating_str = self.get_argument("originating", default=None)
        if originating_str == "true":
            originating = ORIGINATING
        else:
            originating = None
        # auth_type parameter is either set to REGISTRATION_AND_CAPABILITIES or None
        auth_type_str = self.get_argument("auth_type", default=None)
        if auth_type_str == "CAPAB":
            auth_type = REGISTRATION_AND_CAPABILITIES
        else:
            auth_type = None
        retval = yield self.getter(self.application.backend.get_location_information, public_id, originating, auth_type)
        self.send_error_or_response(retval)

