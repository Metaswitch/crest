# @file service_profile.py
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

from .db import ProvisioningModel

PUBLIC_ID_COLUMN_PREFIX = "public_id_"
IFC_COLUMN = "initialfiltercriteria"
IRS_COLUMN = "irs"

class ServiceProfile(ProvisioningModel):
    """Model representing a provisioned service profile"""

    cass_table = config.SP_TABLE

    @defer.inlineCallbacks
    def get_public_ids(self):
        retval = yield self.get_columns_with_prefix_stripped(
                                                        PUBLIC_ID_COLUMN_PREFIX)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_ifc(self):
        retval = yield self.get_columns([IFC_COLUMN])
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_irs(self):
        retval = yield self.get_columns([IRS_COLUMN])
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def associate_public_id(self, public_id):
        yield self.modify_columns({PUBLIC_ID_COLUMN_PREFIX + public_id: None})
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_public_id(self, public_id):
        yield self.delete_column(PUBLIC_ID_COLUMN_PREFIX + public_id)
        yield self.rebuild()

    @defer.inlineCallbacks
    def update_ifc(self, ifc):
        yield self.modify_columns({IFC_COLUMN: ifc})
        yield self.rebuild()

    @defer.inlineCallbacks
    def delete(self):
        public_ids = yield self.get_public_ids()
        for pub_id in public_ids:
            yield PublicID(pub_id).delete()

        irs_uuid = yield self.get_irs()
        IRS(irs_uuid).dissociate_service_profile(self.row_key)

        self.delete_row()

    @defer.inlineCallbacks
    def rebuild(self):
        irs_uuid = yield self.get_irs()
        yield IRS(irs_uuid).rebuild()

