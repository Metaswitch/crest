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

import itertools
from metaswitch.crest.api.homestead.cassandra import CassandraCF, CassandraModel
from metaswitch.crest.api.homestead.backends.provisioning.irs import IRS

class PrivateID(object):
    """Model representing a provisioned private ID"""

    def __init__(self, private_id, cache):
        self._private_id = private_id
        self._cache = cache

        model = CassandraModel("homestead_provisioning")
        self._row = CassandraCF(model, config.PRIVATE_TABLE).row(private_id)

    @staticmethod
    def flatten(list_of_lists):
        """Flatten a list of lists into a single list, e.g:
        flatten([[A, B], [C, D]]) -> [A, B, C, D] """
        return list(itertools.chain.from_iterable(list_of_lists))

    @defer.inlineCallbacks
    def get_digest(self):
        digest = yield self._row.get_columns(["digest_ha1"])
        defer.returnValue(digest)

    @defer.inlineCallbacks
    def get_irses(self):
        irses = yield self._row.get_columns_with_prefix_stripped("associated_irs_")
        defer.returnValue(irses)

    @defer.inlineCallbacks
    def get_public_ids(self):
        irs_uuids = yield self.get_irses()
        public_ids = self.flatten(yield IRS(uuid).get_public_ids()
                                                          for uuid in irs_uuids)
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def put_digest(self, digest):
        yield self._row.modify_columns({"digest_ha1": digest})
        yield self._cache.put_digest(self._private_id, digest)

    @defer.inlineCallbacks
    def delete(self):
        irs_uuids = yield self.get_irses()
        for uuid in irs_uuids:
            yield IRS(uuid).dissociate_private_id(self._private_id)

        yield self._row.delete()
        yield self._cache.delete_private_id(self._private_id)

    @defer.inlineCallbacks
    def associate_irs(self, irs_uuid):
        yield self._row.modify_columns({"associated_irs_%s" % irs_uuid: None})
        yield IRS(uuid).associate_private_id(self._private_id)
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_irs(self, irs_uuid):
        yield self._row.delete_columns(["associated_irs_%s" % irs_uuid])
        yield IRS(uuid).dissociate_private_id(self._private_id)
        yield self.rebuild()

    @defer.inlineCallbacks
    def rebuild(self):
        digest = yield self.get_digest()
        irs_uuids = yield self.get_irses()

        yield self._cache.delete_private_id(self._private_id)
        for irs in irs_uuids:
            for public_id in yield IRS(irs).get_public_ids():
                yield self._cache.put_associated_public_id(private_id, public_id)
        yield self._cache.put_digest(digest)




