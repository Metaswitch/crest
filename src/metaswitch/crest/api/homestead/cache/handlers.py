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
import json

from cyclone.web import HTTPError
from twisted.internet import defer

from metaswitch.crest.api._base import BaseHandler
_log = logging.getLogger("crest.api.homestead.cache")

JSON_DIGEST_HA1 = "digest_ha1"


class DigestHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, private_id):
        public_id = self.get_argument("public_id", default=None)
        retval = yield self.application.cache.get_digest(private_id,
                                                         public_id)
        retval = {JSON_DIGEST_HA1: retval} if retval else None
        self.send_error_or_response(retval)

    @defer.inlineCallbacks
    def put(self, private_id):
        try:
            digest = json.dumps(self.request.body)[JSON_DIGEST_HA1]
            yield self.application.cache.put_digest(digest, private_id)
            self.finish()
        except:
            reason = "Body must be JSON containing a %s key" % JSON_DIGEST_HA1
            raise HTTPError(400, reason)

    def send_error_or_response(self, retval):
        if retval is None:
            self.send_error(404)
        elif isinstance(retval, HTTPError):
            self.send_error(retval.status_code)
        else:
            self.finish(retval)


class IMSSubscriptionHandler(DigestHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        private_id = self.get_argument("private_id", default=None)
        retval = yield self.application.cache.get_IMSSubscription(public_id,
                                                                  private_id)
        self.send_error_or_response(retval)


class iFCHandler(DigestHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        private_id = self.get_argument("private_id", default=None)
        retval = yield self.application.cache.get_iFC(public_id, private_id)
        self.send_error_or_response(retval)
