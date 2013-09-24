# @file private_id.py
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

from twisted.internet import defer

from .db import ProvisioningModel
from .irs import IRS
from ... import config
from metaswitch.crest.api import utils

DIGEST_HA1 = "digest_ha1"
ASSOC_IRS_PREFIX = "associated_irs_"


class PrivateID(ProvisioningModel):
    """Model representing a provisioned private ID"""

    cass_table = config.PRIVATE_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "private_id text PRIMARY KEY, " +
            DIGEST_HA1+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_digest(self):
        digest = yield self.get_column_value(DIGEST_HA1)
        defer.returnValue(digest)

    @defer.inlineCallbacks
    def get_irses(self):
        irses = yield self.get_columns_with_prefix_stripped(ASSOC_IRS_PREFIX)
        defer.returnValue(irses)

    @defer.inlineCallbacks
    def get_public_ids(self):
        irs_uuids = yield self.get_irses()
        public_ids = utils.flatten((yield IRS(uuid).get_public_ids())
                                                          for uuid in irs_uuids)
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def put_digest(self, digest):
        yield self.modify_columns({DIGEST_HA1: digest})
        yield self._cache.put_digest(self.row_key,
                                     digest,
                                     self._cache.generate_timestamp())

    @defer.inlineCallbacks
    def delete(self):
        irs_uuids = yield self.get_irses()
        for uuid in irs_uuids:
            yield IRS(uuid).dissociate_private_id(self.row_key)

        yield self.delete_row()
        yield self._cache.delete_private_id(self.row_key,
                                            self._cache.generate_timestamp())

    @defer.inlineCallbacks
    def associate_irs(self, irs_uuid):
        yield self.assert_row_exists()
        yield self.modify_columns({ASSOC_IRS_PREFIX + str(irs_uuid): None})
        yield IRS(irs_uuid).associate_private_id(self.row_key)
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_irs(self, irs_uuid):
        yield self.delete_columns([ASSOC_IRS_PREFIX + str(irs_uuid)])
        yield IRS(irs_uuid).dissociate_private_id(self.row_key)
        yield self.rebuild()

    @defer.inlineCallbacks
    def rebuild(self):
        """ Rebuild the IMPI table in the cache """

        # Get all the information we need to rebuild the cache.  Do this before
        # deleting any cache entries to minimize the time the cache is empty.
        digest = yield self.get_digest()

        public_ids = []
        for irs in (yield self.get_irses()):
            for pub_id in (yield IRS(irs).get_public_ids()):
                public_ids.append(pub_id)

        timestamp = self._cache.generate_timestamp()

        # Delete the existing cache entry then write back the digest and the
        # associated public IDs.
        yield self._cache.delete_private_id(self.row_key, timestamp)
        yield self._cache.put_digest(digest, timestamp)
        for pub_id in public_ids:
            yield self._cache.put_associated_public_id(self.row_key,
                                                       pub_id,
                                                       timestamp)
