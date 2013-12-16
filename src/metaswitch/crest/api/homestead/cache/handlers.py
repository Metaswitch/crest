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
import time

from cyclone.web import HTTPError
from twisted.internet import defer
from .. import authtypes

from metaswitch.crest import settings
from metaswitch.crest.api.base import BaseHandler, hss_latency_accumulator, cache_latency_accumulator
_log = logging.getLogger("crest.api.homestead.cache")

JSON_DIGEST_HA1 = "digest_ha1"

# auth_type dictionary matching strings defined for URL to enumerated values
# for User-Authorization AVP defined in RFC 4740.
AUTH_TYPES = {"REG" : 0, "DEREG" : 1, "CAPAB" : 2}

# Constant to match the enumerated value for Originating-Request AVP in 3GPP 29.229
ORIGINATING = 0

class CacheApiHandler(BaseHandler):
    def send_error_or_response(self, retval, server_error=False):
        if server_error and retval is None:
            self.send_error(500)
        elif retval is None:
            self.send_error(404)
        elif isinstance(retval, HTTPError):
            self.send_error(retval.status_code)
        else:
            self.finish(retval)

    def sequential_getter_with_latency(self, *funcpairs):
        """Each entry in funcpairs is a pair of a getter function (called to
        get the return value) and an accumulator (which tracks the
        latency of the getter).

        Returns a function that calls each getter function in turn
        until one returns something other than None, and tracks the
        latency of each request (successful or not) in the
        accumulator.
        """
        @defer.inlineCallbacks
        def getter(*pos_args, **kwd_args):
            for getter_function, accumulator_function in funcpairs:
                # Track the latency of each request (in usec)
                start_time = time.time()
                retval = yield getter_function(*pos_args, **kwd_args)
                accumulator_function.accumulate((time.time() - start_time) * 1000000)
                if retval:
                    _log.debug("Got result from %s" % getter_function)
                    defer.returnValue(retval)
                else:
                    _log.debug("No result from %s" % getter_function)
        return getter

    def make_getter(self, function_name, use_cache=True):
        # Can't use getattr here - it doesn't play nicely with the mocking
        if function_name == 'get_ims_subscription':
            backend_get, cache_get = self.application.backend.get_ims_subscription, self.application.cache.get_ims_subscription
        elif function_name == 'get_registration_status':
            backend_get = self.application.backend.get_registration_status
        elif function_name == 'get_location_information':
            backend_get = self.application.backend.get_location_information
        else:
            backend_get, cache_get = self.application.backend.get_av, self.application.cache.get_av
        backend_get_with_latency = [backend_get, hss_latency_accumulator]
        if use_cache:
            # Try the cache first.  If that fails go to the backend.
            cache_get_with_latency = [cache_get, cache_latency_accumulator]
            getter = self.sequential_getter_with_latency(cache_get_with_latency, backend_get_with_latency)
        else:
            getter = self.sequential_getter_with_latency(backend_get_with_latency)
        return getter

    def get_ims_subscription(self, *args, **kwargs):
        getter = self.make_getter('get_ims_subscription')
        return getter(*args, **kwargs)

    def get_av(self, *args, **kwargs):
        getter = self.make_getter('get_av')
        return getter(*args, **kwargs)

    def get_av_from_backend(self, *args, **kwargs):
        getter = self.make_getter('get_av', use_cache=False)
        return getter(*args, **kwargs)

    def get_registration_status(self, *args, **kwargs):
        getter = self.make_getter('get_registration_status', use_cache=False)
        return getter(*args, **kwargs)

    def get_location_information(self, *args, **kwargs):
        getter = self.make_getter('get_location_information', use_cache=False)
        return getter(*args, **kwargs)

class DigestHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, private_id):
        public_id = self.get_argument("public_id", default=None)

        auth = yield self.get_av(private_id, public_id, authtypes.SIP_DIGEST, None)

        retval = {JSON_DIGEST_HA1: auth.ha1} if auth else None
        self.send_error_or_response(retval)


class AuthVectorHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, private_id, string_authtype=None):
        public_id = self.get_argument("impu", default=None)
        autn = self.get_argument("autn", default=None)

        authtype = authtypes.UNKNOWN
        if string_authtype == "digest":
            authtype = authtypes.SIP_DIGEST
        elif string_authtype == "aka":
            authtype = authtypes.AKA


        if authtype == authtypes.AKA:
            auth = yield self.get_av_from_backend(private_id, public_id, authtype, autn)
        else:
            auth = yield self.get_av(private_id, public_id, authtype, autn)

        retval = auth.to_json() if auth else None
        self.send_error_or_response(retval)


class IMSSubscriptionHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, public_id):
        private_id = self.get_argument("private_id", default=None)

        retval = yield self.get_ims_subscription(public_id, private_id)
        self.send_error_or_response(retval)

class RegistrationStatusHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, private_id):
        public_id = self.get_argument("impu", default=None)
        visited_network = self.get_argument("visited-network", default=settings.SIP_DIGEST_REALM)
        auth_type_str = self.get_argument("auth_type", default=None)
        auth_type = AUTH_TYPES[auth_type_str] if auth_type_str in AUTH_TYPES.keys() else AUTH_TYPES["REG"]
        retval = yield self.get_registration_status(private_id, public_id, visited_network, auth_type)
        self.send_error_or_response(retval, True)

class LocationInformationHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, public_id):
        # originating parameter should be set to true or we ignore it
        originating_str = self.get_argument("originating", default=None)
        originating = ORIGINATING if originating_str == "true" else None
        # auth_type parameter should be set to CAPAB or we ignore it
        auth_type_str = self.get_argument("auth_type", default=None)
        auth_type = AUTH_TYPES["CAPAB"] if auth_type_str == "CAPAB" else None
        retval = yield self.get_location_information(public_id, originating, auth_type)
        self.send_error_or_response(retval, True)

