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

from metaswitch.crest.api.homestead.cassandra import CassandraCF, CassandraRow
from twisted.internet import defer

PUBLIC_ID_PREFIX = "public_id_"
CASS_DIGEST_HA1 = "digest_ha1"
IMSSUBSCRIPTION = "ims_subscription_xml"
IFC = "initial_filter_criteria_xml"


class IMPI(CassandraCF):
    def row(self, row_key):
        return IMPIRow(self.client, self.cf, row_key)


class IMPIRow(CassandraRow):
    @defer.inlineCallbacks
    def get_digest_ha1(self, public_id):
        public_id_column = PUBLIC_ID_PREFIX+str(public_id)
        columns = yield self.get_columns([CASS_DIGEST_HA1, public_id_column])
        if (CASS_DIGEST_HA1 in columns) and \
           (public_id is None or public_id_column in columns):
            defer.returnValue(columns[CASS_DIGEST_HA1])


class IMPU(CassandraCF):
    def row(self, row_key):
        return IMPURow(self.client, self.cf, row_key)


class IMPURow(CassandraRow):
    @defer.inlineCallbacks
    def get_iFCXML(self):
        columns = yield self.get_columns([IFC])
        if columns:
            defer.returnValue(columns[IFC])

    @defer.inlineCallbacks
    def get_IMSSubscriptionXML(self):
        columns = yield self.get_columns([IMSSUBSCRIPTION])
        if columns:
            defer.returnValue(columns[IMSSUBSCRIPTION])
