# @file public_id.py
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
from .service_profile import ServiceProfile
from ... import config

SERVICE_PROFILE = "service_profile"
PUBLICIDENTITY = "publicidentity"

class PublicID(ProvisioningModel):
    """Model representing a provisioned public identity"""

    cass_table = config.PUBLIC_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "public_id text PRIMARY KEY, " +
            PUBLICIDENTITY+" text, " +
            SERVICE_PROFILE+" uuid" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_sp(self):
        sp_uuid = yield self.get_column_value(SERVICE_PROFILE)
        defer.returnValue(sp_uuid)

    @defer.inlineCallbacks
    def get_publicidentity(self):
        xml = yield self.get_column_value(PUBLICIDENTITY)
        defer.returnValue(xml)

    @defer.inlineCallbacks
    def get_irs(self):
        sp_uuid = yield self.get_sp()
        irs_uuid = yield ServiceProfile(sp_uuid).get_irs()
        defer.returnValue(irs_uuid)

    @defer.inlineCallbacks
    def get_private_ids(self):
        irs_uuid = yield self.get_irs()
        private_ids = yield IRS(irs_uuid).get_private_ids()
        defer.returnValue(private_ids)

    @defer.inlineCallbacks
    def put_publicidentity(self, xml):
        yield self.modify_columns({PUBLICIDENTITY: xml})

    @defer.inlineCallbacks
    def delete(self):
        irs_uuid = yield self.get_irs()
        sp_uuid = yield self.get_sp()

        yield ServiceProfile(sp_uuid).dissociate_public_id(self.row_key)
        yield self.delete_row()
        yield self._cache.delete_public_id(self.row_key,
                                           self._cache.generate_timestamp())

        yield IRS(irs_uuid).rebuild()
