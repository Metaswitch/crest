# @file cassandra.py
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
from telephus.protocol import ManagedCassandraClientFactory
from telephus.client import CassandraClient

class CassandraModel(object):
    def __init__(self, keyspace):
        factory = ManagedCassandraClientFactory(keyspace)
        self.cass = CassandraClient(factory)

    def cf(self, cf):
        return CassandraCF(self.cass, cf)

class CassandraCF(object):
    def __init__(self, client, cf):
        self.client, self.cf = client, cf

    def row(self, row_key):
       return CassandraRow(self.cass, self.cf, row_key)

class CassandraRow(object):
    def __init__(self, client, cf, row_key):
        self.client, self.cf, self.row_key = client, cf, row_key

    @defer.inlineCallbacks
    def get_columns(self, columns=None):
        yield self.client.get_slice(key=self.row_key, column_family=self.cf, names=columns)

    @defer.inlineCallbacks
    def get_columns_with_prefix(self, prefix):
        columns = yield self.client.get(key=self.row_key, column_family=self.cf)
        desired_pairs = {}
        for col in columns:
            if col.column.name.startswith(prefix):
                desired_pairs[col.column.name] = col.column.value
        defer.returnValue(desired_pairs)

    @defer.inlineCallbacks
    def get_columns_with_prefix_stripped(self, prefix):
        mapping = yield get_columns_with_prefix(prefix)
        new_mapping = {key.lstrip(prefix): value for key, value in mapping.iteritems()}
        defer.returnValue(new_mapping)
    
    @defer.inlineCallbacks
    def modify_columns(self, mapping, ttl=None):
        yield self.client.batch_insert(key=self.row_key, column_family=self.cf, mapping=mapping, ttl=ttl)
