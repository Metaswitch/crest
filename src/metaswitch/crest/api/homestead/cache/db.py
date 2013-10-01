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

from twisted.internet import defer

from .. import config
from ..cassandra import CassandraModel
from telephus.cassandra.ttypes import NotFoundException

DIGEST_HA1 = "digest_ha1"
PUBLIC_ID_PREFIX = "public_id_"


class CacheModel(CassandraModel):
    cass_keyspace = config.CACHE_KEYSPACE


class IMPI(CacheModel):
    cass_table = config.IMPI_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "private_id text PRIMARY KEY, " +
            DIGEST_HA1+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_digest_ha1(self, public_id):
        try:
            query_columns = [DIGEST_HA1]
            if public_id:
                public_id_column = PUBLIC_ID_PREFIX+str(public_id)
                query_columns.append(public_id_column)

            columns = yield self.get_columns(query_columns)

            if (DIGEST_HA1 in columns) and \
               (public_id is None or public_id_column in columns):
                defer.returnValue(columns[DIGEST_HA1])

        except NotFoundException:
            pass


    @defer.inlineCallbacks
    def put_digest_ha1(self, digest, timestamp=None):
        yield self.modify_columns({DIGEST_HA1: digest}, timestamp=timestamp)

    @defer.inlineCallbacks
    def put_associated_public_id(self, public_id, timestamp=None):
        public_id_column = PUBLIC_ID_PREFIX + public_id
        yield self.modify_columns({public_id_column: ""}, timestamp=timestamp)


IMS_SUBSCRIPTION = "ims_subscription_xml"


class IMPU(CacheModel):
    cass_table = config.IMPU_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "public_id text PRIMARY KEY, " +
            IMS_SUBSCRIPTION+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_ims_subscription(self):
        try:
            retval = yield self.get_column_value(IMS_SUBSCRIPTION)
            defer.returnValue(retval)

        except NotFoundException:
            pass

    @defer.inlineCallbacks
    def put_ims_subscription(self, ims_subscription, timestamp=None):
        yield self.modify_columns({IMS_SUBSCRIPTION: ims_subscription},
                                  timestamp=timestamp)
