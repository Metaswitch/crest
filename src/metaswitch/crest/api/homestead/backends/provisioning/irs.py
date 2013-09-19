# @file irs.py
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

from metaswitch.crest.api.homestead.cassandra import CassandraCF, CassandraModel

class IRS(object):
    """Model representing an implicit registration set"""

    def __init__(self, uuid, cache):
        self._uuid = uuid
        self._cache = cache

        model = CassandraModel("homestead_provisioning")
        self._row = CassandraCF(model, config.IRS_TABLE).row(uuid)

    @staticmethod
    def flatten(list_of_lists):
        """Flatten a list of lists into a single list, e.g:
        flatten([[A, B], [C, D]]) -> [A, B, C, D] """
        return list(itertools.chain.from_iterable(list_of_lists))

    @defer.inlineCallbacks
    def get_associated_privates(self):
        retval = yield self._row.get_columns_with_prefix_stripped("associated_private_")
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_associated_service_profiles(self):
        retval = yield self._row.get_columns_with_prefix_stripped("service_profile_")
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_associated_publics(self):
        sp_uuids = yield self.get_associated_service_profiles()
        public_ids = self.flatten(yield ServiceProfile(uuid).get_public_ids()
                                                           for uuid in sp_uuids)
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def associate_private_id(self, private_id):
        yield self._row.modify_columns({"associated_private_%s" % private_id: None})

    @defer.inlineCallbacks
    def dissociate_private_id(self):
        yield self._row.delete_columns(["associated_private_%s" % private_id])

    @defer.inlineCallbacks
    def associate_service_profile(self, sp_uuid):
        yield self._row.modify_columns({"service_profile_%s" % sp_uuid: None})
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_Service_profile(self, sp_uuid):
        yield self._row.delete_columns(["service_profile_%s" % sp_uuid])
        yield self.rebuild()

    @defer.inlineCallbacks
    def delete(self):
        sp_uuids = yield self.get_associated_service_profiles()
        for uuid in sp_uuids:
            yield ServiceProfile(uuid).delete()

        private_ids = yield self.get_associated_privates()
        for priv in private_ids:
            yield PrivateID(priv).dissociate_irs(self._uuid)

        self._row.delete()

    @defer.inlineCallbacks
    def rebuild(self):
        # TODO
        service_profiles = yield self.get_associated_service_profiles()
        public_ids = yield self.get_associated_publics()
        private_ids = yield self.get_associated_privates()




