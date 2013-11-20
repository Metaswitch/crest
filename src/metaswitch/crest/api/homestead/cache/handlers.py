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

from metaswitch.crest.api.base import BaseHandler, hss_latency_accumulator, cache_latency_accumulator
_log = logging.getLogger("crest.api.homestead.cache")

JSON_DIGEST_HA1 = "digest_ha1"


class CacheApiHandler(BaseHandler):


    def send_error_or_response(self, retval):
        if retval is None:
            self.send_error(404)
        elif isinstance(retval, HTTPError):
            self.send_error(retval.status_code)
        else:
            self.finish(retval)

    @staticmethod
    def sequential_getter_with_latency(*funcpairs):
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


class DigestHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, private_id):
        public_id = self.get_argument("public_id", default=None)

        cache_get = [self.application.cache.get_av, cache_latency_accumulator]
        backend_get = [self.application.backend.get_av, hss_latency_accumulator]

        # Try the cache first.  If that fails go to the backend.
        getter = self.sequential_getter_with_latency(cache_get, backend_get)
        auth = yield getter(private_id, public_id, authtypes.SIP_DIGEST, None)

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

        cache_get = [self.application.cache.get_av, cache_latency_accumulator]
        backend_get = [self.application.backend.get_av, hss_latency_accumulator]

        if authtype == authtypes.AKA:
            getter = self.sequential_getter_with_latency(backend_get)
        else:
            # Try the cache first.  If that fails go to the backend.
            getter = self.sequential_getter_with_latency(cache_get, backend_get)
        auth = yield getter(private_id, public_id, authtype, autn)

        retval = auth.to_json() if auth else None
        self.send_error_or_response(retval)


class IMSSubscriptionHandler(CacheApiHandler):
    @BaseHandler.check_request_age
    @defer.inlineCallbacks
    def get(self, public_id):
        private_id = self.get_argument("private_id", default=None)

        # Try the cache first.  If that fails go to the backend.
        getter = self.sequential_getter_with_latency(
                 [self.application.cache.get_ims_subscription, cache_latency_accumulator],
                 [self.application.backend.get_ims_subscription, hss_latency_accumulator])
        retval = yield getter(public_id, private_id)
        self.send_error_or_response(retval)
