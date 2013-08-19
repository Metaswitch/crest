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

from twisted.internet import defer, reactor
from metaswitch.crest.api import settings
from telephus.protocol import ManagedCassandraClientFactory
from telephus.client import CassandraClient, ConsistencyLevel
from telephus.cassandra.ttypes import NotFoundException, UnavailableException


class CassandraModel(object):
    """Simple representation of a Cassandra keyspace"""
    def __init__(self, keyspace):
        factory = ManagedCassandraClientFactory(keyspace)
        reactor.connectTCP(settings.CASS_HOST, settings.CASS_PORT, factory)
        self.client = CassandraClient(factory)


class CassandraCF(object):
    """Simple representation of a Cassandra column family"""
    def __init__(self, model, cf):
        self.client, self.cf = model.client, cf

    def get_row(self, row_key):
        return CassandraRow(self.client, self.cf, row_key)


class CassandraRow(object):
    """Simple representation of a Cassandra row"""
    def __init__(self, client, cf, row_key):
        self.client, self.cf, self.row_key = client, cf, row_key

    @defer.inlineCallbacks
    def get_columns(self, columns=None):
        """Gets the named columns from this row (or all columns if it is not
specified). Returns the columns formatted as a dictionary.
Does not support super columns."""
        columns = yield self.ha_get_slice(key=self.row_key,
                                          column_family=self.cf,
                                          names=columns)
        columns_as_dictionary = {col.column.name: col.column.value
                                 for col in columns}
        defer.returnValue(columns_as_dictionary)

    @defer.inlineCallbacks
    def get_columns_with_prefix(self, prefix):
        """Gets all columns with the given prefix from this row.
Returns the columns formatted as a dictionary.
Does not support super columns."""
        columns = yield self.ha_get(key=self.row_key, column_family=self.cf)
        desired_pairs = {k: v for k, v in columns if k.startswith(prefix)}
        defer.returnValue(desired_pairs)

    @defer.inlineCallbacks
    def get_columns_with_prefix_stripped(self, prefix):
        """Gets all columns with the given prefix from this row.
Returns the columns formatted as a dictionary,
with the prefix stripped off the keys.
Does not support super columns."""
        mapping = yield self.get_columns_with_prefix(prefix)
        new_mapping = {key.lstrip(prefix): value
                       for key, value in mapping.iteritems()}
        defer.returnValue(new_mapping)

    @defer.inlineCallbacks
    def modify_columns(self, mapping, ttl=None):
        """Updates this row to give the columns specified by the keys of
`mapping` their respective values."""
        yield self.client.batch_insert(key=self.row_key,
                                       column_family=self.cf,
                                       mapping=mapping,
                                       ttl=ttl)

    # After growing a cluster, Cassandra does not pro-actively populate the
    # new nodes with their data (the nodes are expected to use `nodetool
    # repair` if they need to get their data).  Combining this with
    # the fact that we generally use consistency ONE when reading data, the
    # behaviour on new nodes is to return NotFoundException or empty result
    # sets to queries, even though the other nodes have a copy of the data.
    #
    # To resolve this issue, these two functions can be used as drop-in
    # replacements for `CassandraClient#get` and `CassandraClient#get_slice`
    # and will attempt a QUORUM read in the event that a ONE read returns
    # no data.  If the QUORUM read fails due to unreachable nodes, the
    # original result will be returned (i.e. an empty set or NotFound).
    @defer.inlineCallbacks
    def ha_get(self, *args, **kwargs):
        try:
            result = yield self.client.get(*args, **kwargs)
            defer.returnValue(result)
        except NotFoundException as e:
            kwargs['consistency'] = ConsistencyLevel.QUORUM
            try:
                result = yield self.client.get(*args, **kwargs)
                defer.returnValue(result)
            except (NotFoundException, UnavailableException):
                raise e

    @defer.inlineCallbacks
    def ha_get_slice(self, *args, **kwargs):
        result = yield self.client.get_slice(*args, **kwargs)
        if len(result) == 0:
            kwargs['consistency'] = ConsistencyLevel.QUORUM
            try:
                qresult = yield self.client.get_slice(*args, **kwargs)
                result = qresult
            except UnavailableException:
                pass
        defer.returnValue(result)
