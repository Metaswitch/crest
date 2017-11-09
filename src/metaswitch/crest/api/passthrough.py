# @file passthrough.py
#
# Copyright (C) Metaswitch Networks 2013
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


import logging
import httplib

from cyclone.web import HTTPError
from telephus.client import CassandraClient
from telephus.cassandra.ttypes import NotFoundException, UnavailableException, ConsistencyLevel
from twisted.internet import defer

from metaswitch.crest.api.base import BaseHandler

_log = logging.getLogger("crest.api")


class PassthroughHandler(BaseHandler):
    """
    The passthrough handler simply takes what has been sent in from the router
    and reads/writes/deletes without any validation.

    Handlers should subclass this handler in order to do parameter validation. After
    validation, the handlers should call through the passthrough handler to write to the
    database
    """

    cass_factories = {}

    @classmethod
    def add_cass_factory(cls, factory_name, factory):
        cls.cass_factories[factory_name] = factory

    def initialize(self, factory_name, table, column):
        """
        The factory_name, table and column are set as part of the Application router, see api/__init__.py

        The table corresponds to the cassandra table, while the column specifies the cassandra column to operate on
        The row to operate on is passed to each function, while the value is in the request body, if relevant
        """
        self.table = table
        self.column = column
        self.cass = CassandraClient(self.cass_factories[factory_name])

    @defer.inlineCallbacks
    def get(self, row):
        try:
            result = yield self.ha_get(column_family=self.table, key=row, column=self.column)
            self.finish(result.column.value)
        except NotFoundException:
            raise HTTPError(404)

    # POST is difficult to generalize as it resource-specific - so force subclasses to implement
    def post(self, *args):
        raise HTTPError(405)

    @defer.inlineCallbacks
    def put(self, row):
        yield self.cass.insert(column_family=self.table, key=row, column=self.column, value=self.request.body)
        self.finish({})

    @defer.inlineCallbacks
    def delete(self, row):
        yield self.cass.remove(column_family=self.table, key=row, column=self.column)
        self.set_status(httplib.NO_CONTENT)
        self.finish()

    # After growing a cluster, Cassandra does not pro-actively populate the
    # new nodes with their data (the nodes are expected to use `nodetool
    # repair` if they need to get their data).
    #
    @defer.inlineCallbacks
    def ha_get(self, *args, **kwargs):
        kwargs['consistency'] = ConsistencyLevel.LOCAL_QUORUM
        try:
            result = yield self.cass.get(*args, **kwargs)
            defer.returnValue(result)
        except UnavailableException as e:
            try:
                kwargs['consistency'] = ConsistencyLevel.ONE
                result = yield self.cass.get(*args, **kwargs)
                defer.returnValue(result)
            except (NotFoundException, UnavailableException) as e:
                raise e

    @defer.inlineCallbacks
    def ha_get_slice(self, *args, **kwargs):
        kwargs['consistency'] = ConsistencyLevel.LOCAL_QUORUM
        try:
            result = yield self.cass.get_slice(*args, **kwargs)
            defer.returnValue(result)
        except UnavailableException as e:
            try:
                kwargs['consistency'] = ConsistencyLevel.ONE
                result = yield self.cass.get_slice(*args, **kwargs)
                defer.returnValue(result)
            except (NotFoundException, UnavailableException) as e:
                raise e
