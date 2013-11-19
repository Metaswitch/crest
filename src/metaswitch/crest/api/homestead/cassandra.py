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
from telephus.cassandra.ttypes import Column, Deletion, NotFoundException, UnavailableException


class CassandraConnection(object):
    """Simple representation of a connection to a Cassandra keyspace"""
    def __init__(self, keyspace):
        self._keyspace = keyspace

        factory = ManagedCassandraClientFactory(keyspace)
        reactor.connectTCP(settings.CASS_HOST, settings.CASS_PORT, factory)
        self.client = CassandraClient(factory)


class CassandraModel(object):
    """Simple representation of a Cassandra row"""

    # When doing a get Telephus does not distinguish between a row that doesn't
    # exist, or a row where none of the columns matched the predicate.  It is
    # useful to know whether a row exists or not, so we add a column that is
    # always present and we can query to tell if this is the case.
    EXISTS_COLUMN = "_exists"

    @classmethod
    def start_connection(cls):
        """Connect to cassandra.

        This is done in a class method (rather than as part of class definition)
        to make unit testing without a real cassandra database possible"""
        cls.cass_connection = CassandraConnection(cls.cass_keyspace)
        cls.client = cls.cass_connection.client

    def __init__(self, row_key):
        self.row_key = row_key
        self.row_key_str = str(row_key)

    @defer.inlineCallbacks
    def get_columns(self, columns=None):
        """Gets the named columns from this row (or all columns if it is not
        specified). Returns the columns formatted as a dictionary.
        Does not support super columns."""

        # If we've not been asked for all columns, also query the 'created'
        # column as well (but don't modify the list that was passed in).
        if columns:
            columns = list(columns)
            columns.append(self.EXISTS_COLUMN)

        cass_columns = yield self.ha_get_slice(key=self.row_key,
                                               column_family=self.cass_table,
                                               names=columns)

        # Raise NotFoundException if the row doesn't exist.
        if not cass_columns:
            raise NotFoundException

        columns_as_dictionary = {col.column.name: col.column.value
                                 for col in cass_columns}

        # Don't return the internal "exists" column to the user.
        if self.EXISTS_COLUMN in columns_as_dictionary:
            del columns_as_dictionary[self.EXISTS_COLUMN]

        defer.returnValue(columns_as_dictionary)

    @defer.inlineCallbacks
    def get_column_value(self, column):
        """Gets the value of a single named column"""
        try:
            column_dict = yield self.get_columns([column])
            defer.returnValue(column_dict[column])
        except KeyError:
            raise NotFoundException

    @defer.inlineCallbacks
    def get_columns_with_prefix(self, prefix):
        """Gets all columns with the given prefix from this row.
        Returns the columns formatted as a dictionary.
        Does not support super columns."""
        columns = yield self.get_columns()
        desired_pairs = {k: v for k, v in columns.items() if k.startswith(prefix)}
        defer.returnValue(desired_pairs)

    @defer.inlineCallbacks
    def get_columns_with_prefix_stripped(self, prefix):
        """Gets all columns with the given prefix from this row.
        Returns the columns formatted as a dictionary,
        with the prefix stripped off the keys.
        Does not support super columns."""
        mapping = yield self.get_columns_with_prefix(prefix)
        new_mapping = {key[len(prefix):]: value
                       for key, value in mapping.iteritems()
                       if key.startswith(prefix)}
        defer.returnValue(new_mapping)

    @defer.inlineCallbacks
    def touch(self):
        """Ensure this row exists in the database, but don't change/set any
        columns."""
        yield self.modify_columns({})

    @defer.inlineCallbacks
    def modify_columns(self, mapping, ttl=None, timestamp=None):
        """Updates this row to give the columns specified by the keys of
        `mapping` their respective values."""

        # Also write the 'exists' column, but don't modify the dictionary that
        # was passed in.
        mapping = dict(mapping)
        mapping[self.EXISTS_COLUMN] = ""

        yield self.client.batch_insert(key=self.row_key,
                                       column_family=self.cass_table,
                                       mapping=mapping,
                                       ttl=ttl,
                                       timestamp=timestamp)

    @classmethod
    @defer.inlineCallbacks
    def modify_columns_multikeys(cls, keys, mapping, ttl=None, timestamp=None):
        """Updates a set of rows to give the columns specified by the keys of
        `mapping` their respective values."""
        row = map(lambda x: Column(x, mapping[x], timestamp, ttl), mapping)
        row.append(Column(cls.EXISTS_COLUMN, "", timestamp, ttl))
        mutmap = {key: {cls.cass_table: row} for key in keys}
        yield cls.client.batch_mutate(mutmap)

    @defer.inlineCallbacks
    def delete_row(self, timestamp=None):
        """Delete this entire row"""
        yield self.client.remove(key=self.row_key,
                                 column_family=self.cass_table,
                                 timestamp=timestamp)

    @classmethod
    @defer.inlineCallbacks
    def delete_rows(cls, keys, timestamp=None):
        """Delete multiple row"""
        mutmap = {}
        row = [Deletion(timestamp)]
        mutmap = {key: {cls.cass_table: row} for key in keys}
        yield cls.client.batch_mutate(mutmap)

    @defer.inlineCallbacks
    def delete_column(self, column_name, timestamp=None):
        """Delete a single column from the row"""
        yield self.client.remove(key=self.row_key,
                                 column_family=self.cass_table,
                                 column=column_name,
                                 timestamp=timestamp)

    @classmethod
    @defer.inlineCallbacks
    def row_exists(self, row_key):
        """
        Returns whether a row exists with the specified key

        This is determined by issuing a get on all columns and checking for
        NotFoundException.
        """
        try:
            yield self.get_columns()
            exists = True
        except NotFoundException:
            exists = False

        defer.returnValue(exists)

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
