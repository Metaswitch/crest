# @file public.py
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

from twisted.internet import defer, reactor
from telephus.cassandra.ttypes import NotFoundException
from metaswitch.crest.api.base import BaseHandler, SlowRequestHandler
import json
import logging

from ..models import PublicID

_log = logging.getLogger("crest.api.homestead.provisioning")

# Twisted-friendly non-blocking sleep function
def sleep(seconds):
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, seconds)
    return d


JSON_PRIVATE_IDS = "private_ids"

class AllPublicIDsHandler(SlowRequestHandler):
    @defer.inlineCallbacks
    def get(self):
        num_chunks = int(self.get_argument("chunk-proportion", default=256))
        chunk = self.get_argument("chunk", default="")
        chunk = int(chunk) if chunk != "" else None
        fast = (self.get_argument("excludeuuids", default="false") == "true")

        # Break the Cassandra ring down into chunks
        min_token = -2**63;
        max_token = (2**63)-1;

        chunk_size = (max_token - min_token) / num_chunks

        if chunk != None:
            _log.info("Retrieving public IDs (chunk {}/{})".format(chunk, num_chunks))
            start = min_token + chunk * chunk_size
            max_start = min([max_token, start + chunk_size])
        else:
            _log.info("Retrieving all public IDs (broken into {} chunks)".format(num_chunks))
            start = min_token
            max_start = max_token

        # Query all subscribers, chunk-by-chunk, and stream it back to the
        # client
        first_result = True
        first_chunk = True

        self.write('{"public_ids": [')
        while start < max_start:
            if not first_chunk:
                # Write some data to prevent the request from being timed out by
                # nginx. Use a space as whitespace is not significant in JSON.
                self.write(' ')

                # Sleep to avoid using too much CPU. Don't sleep on the first
                # iteration as this makes the request take at least 1 second
                # (which is bad for tools which query small subsections of the
                # token space).
                yield sleep(1)

            end = min([max_token, start + chunk_size])
            result = yield PublicID.get_chunk(start=str(start), finish=str(end))
            for p in result:
                sp = None
                irs = None

                if first_result:
                    first_result = False
                else:
                    self.write(',')

                # Retrieving these UUIDs is time-consuming and may not be
                # necessary - skip them if "excludeuuids=true" is given in the URL.
                if not fast:
                    sp = yield p.get_sp_str()
                    irs = yield p.get_irs_str()
                    self.write(json.dumps({"public_id": p.row_key_str,
                                           "sp": sp,
                                           "irs": irs
                                          }))
                else:
                    self.write(json.dumps({"public_id": p.row_key_str}))

            self.flush()
            start = end

            first_chunk = False

        self.write(']}')

        self.finish()


class PublicIDServiceProfileHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        try:
            pub = PublicID(public_id)
            sp_uuid = yield pub.get_sp()
            irs_uuid = yield pub.get_irs()

            self.set_header("Location", "/irs/%s/service_profiles/%s" %
                                                            (irs_uuid, sp_uuid))
            self.set_status(303)
            self.finish()

        except NotFoundException:
            self.send_error(404)


class PublicIDIRSHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        try:
            irs_uuid = yield PublicID(public_id).get_irs()
            self.set_header("Location", "/irs/%s" % irs_uuid)
            self.set_status(303)
            self.finish()

        except NotFoundException:
            self.send_error(404)


class PublicIDPrivateIDHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, public_id):
        try:
            private_ids = yield PublicID(public_id).get_private_ids()
            self.send_json({JSON_PRIVATE_IDS: private_ids})

        except NotFoundException:
            self.send_error(404)
