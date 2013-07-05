# @file associatedURIs.py
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


import logging
import httplib

from cyclone.web import HTTPError
from telephus.cassandra.ttypes import NotFoundException
from twisted.internet import defer

from metaswitch.crest.api.passthrough import PassthroughHandler
from metaswitch.crest import settings
from metaswitch.common import utils
from metaswitch.crest.api.homestead import config

_log = logging.getLogger("crest.api.homestead")

class AssociatedURIsHandler(PassthroughHandler):
    """
    Handler for AssociatedURIs

    This class contains all code that is shared between the handlers for
    associatedpublic (public IDs associated with a private ID) and
    associatedprivate (private IDs associated with a public ID) APIs.

    This handler is called on both the associatedpublic and associatedprivate
    URIs.  So the methods need to handle GET/POST/DELETE that are primarily
    indexed on both public and private IDs.

    """
    def put(self, *args):
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)

    @defer.inlineCallbacks
    def insert_in_both_tables(self, private_id, public_id):

        # Check whether this association already exists - choice of 200/201
        # status depends on this
        exists = False
        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=config.PUBLIC_IDS_TABLE,
                                            start=public_id,
                                            finish=public_id)

        for record in db_data:
            exists = (record.column.name == public_id)

        if exists:
            self.set_status(httplib.OK)
        else:
            # check that neither pri nor public ID is at limit of allowed associations
            d1 = self.cass.get_slice(key=private_id,
                                     column_family=config.PUBLIC_IDS_TABLE)
            d2 = self.cass.get_slice(key=public_id,
                                     column_family=config.PRIVATE_IDS_TABLE)
            pub_ids = yield d1
            priv_ids = yield d2

            if len(pub_ids) >= config.MAX_ASSOCIATED_PUB_IDS:
                raise HTTPError(httplib.BAD_REQUEST, "", {"reason":"Associated Public Identity limit reached"})

            if len(priv_ids) >= config.MAX_ASSOCIATED_PRI_IDS:
                raise HTTPError(httplib.BAD_REQUEST, "", {"reason":"Associated Private Identity limit reached"})

            try:
                # Insert in both tables. If either insert fails for any reason
                # at all, remove both entries so that the tables stay in step.
                d1 = self.cass.insert(column_family=config.PUBLIC_IDS_TABLE,
                                      key=private_id,
                                      column=public_id,
                                      value=public_id)
                d2 = self.cass.insert(column_family=config.PRIVATE_IDS_TABLE,
                                      key=public_id,
                                      column=private_id,
                                      value=private_id)
                yield d1
                yield d2
            except:
                d3 = self.cass.remove(column_family=config.PUBLIC_IDS_TABLE,
                                      key=private_id,
                                      column=public_id,
                                      value=public_id)
                d4 = self.cass.remove(column_family=config.PRIVATE_IDS_TABLE,
                                      key=public_id,
                                      column=private_id,
                                      value=private_id)
                yield d3
                yield d4
                raise HTTPError(httplib.INTERNAL_SERVER_ERROR)

            self.set_status(httplib.CREATED)

    @defer.inlineCallbacks
    def delete_from_both_tables(self, private_id, public_id):
        d1 = self.cass.remove(column_family=config.PUBLIC_IDS_TABLE, key=private_id, column=public_id)
        d2 = self.cass.remove(column_family=config.PRIVATE_IDS_TABLE, key=public_id, column=private_id)
        yield d1
        yield d2


class AssociatedPrivateHandler(AssociatedURIsHandler):
    """
    Handler for AssociatedPrivate - GET/POST/DELETE to query/add/remove
    private IDs associated to a public ID.

    """
    @defer.inlineCallbacks
    def get(self, public_id, private_id=None):
        if private_id is not None:
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)

        db_data = yield self.cass.get_slice(key=public_id,
                                            column_family=self.table)

        private_ids = []
        for record in db_data:
            private_ids.append(record.column.value)

        if private_ids == []:
            # Note: The get_slice API does not throw a NotFoundException if it
            # finds no matches
            raise HTTPError(httplib.NOT_FOUND)

        self.finish({"public_id": public_id, "private_ids": private_ids})

    @defer.inlineCallbacks
    def post(self, public_id, private_id=None):
        if private_id is not None:
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)
        else:
            private_id = self.request_data.get("private_id", "")
            if private_id == "":
                raise HTTPError(httplib.METHOD_NOT_ALLOWED)

        yield self.insert_in_both_tables(private_id, public_id)

        # Retrieve the updated full list of public IDs associated with this private ID
        db_data = yield self.cass.get_slice(key=public_id,
                                            column_family=self.table)
        private_ids = []
        for record in db_data:
            private_ids.append(record.column.value)

        self.finish({"public_id": public_id, "private_ids": private_ids})

    @defer.inlineCallbacks
    def delete(self, public_id, private_id=None):
        if private_id is not None:
            yield self.delete_from_both_tables(private_id, public_id)
        else:
            db_data = yield self.cass.get_slice(key=public_id,
                                                column_family=self.table)

            for record in db_data:
                yield self.delete_from_both_tables(record.column.value, public_id)

        self.set_status(httplib.NO_CONTENT)
        self.finish()


class AssociatedPublicHandler(AssociatedURIsHandler):
    """
    Handler for AssociatedPublic

    Handler for AssociatedPrivate - GET/POST/DELETE to query/add/remove
    public IDs associated to a private ID.

    """
    @defer.inlineCallbacks
    def get(self, private_id, public_id=None):
        if public_id is not None:
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)

        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=self.table)

        public_ids = []
        for record in db_data:
            public_ids.append(record.column.value)
        if public_ids == []:
            raise HTTPError(httplib.NOT_FOUND)

        self.finish({"private_id": private_id, "public_ids": public_ids})

    @defer.inlineCallbacks
    def post(self, private_id, public_id=None):
        if public_id is not None:
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)
        else:
            public_id = self.request_data.get("public_id", "")
            if public_id == "":
                raise HTTPError(httplib.METHOD_NOT_ALLOWED)

        yield self.insert_in_both_tables(private_id, public_id)

        # Retrieve the updated full list of public IDs associated with this private ID
        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=self.table)
        public_ids = []
        for record in db_data:
            public_ids.append(record.column.value)

        self.finish({"private_id": private_id, "public_ids": public_ids})

    @defer.inlineCallbacks
    def delete(self, private_id, public_id=None):
        if public_id is not None:
            yield self.delete_from_both_tables(private_id, public_id)
        else:
            db_data = yield self.cass.get_slice(key=private_id,
                                                column_family=self.table)
            for record in db_data:
                yield self.delete_from_both_tables(private_id, record.column.value)

        self.set_status(httplib.NO_CONTENT)
        self.finish()

class AssociatedPublicByPublicHandler(AssociatedURIsHandler):
    """
    Handler for AssociatedPublicByPublic

    Handler for AssociatedPrivate - GET to retrieve the full list of public IDs
    associated to the private ID associated to the supplied public ID.
    This interface is READONLY - no PUT/POST/DELETE.

    """
    @defer.inlineCallbacks
    def get(self, public_id):

        db_data = yield self.cass.get_slice(key=public_id,
                                            column_family=config.PRIVATE_IDS_TABLE)

        private_ids = []
        for record in db_data:
            private_ids.append(record.column.value)
        if private_ids == []:
            raise HTTPError(httplib.NOT_FOUND)

        # Currently only permit one private ID per public ID.
        assert(len(private_ids) == 1)

        db_data = yield self.cass.get_slice(key=private_ids[0],
                                            column_family=config.PUBLIC_IDS_TABLE)

        public_ids = []
        for record in db_data:
            public_ids.append(record.column.value)

        assert(public_ids != [])  # There are probably tiny windows in which this
                                  # is not the case. Best strategy?

        self.finish({"public_ids": public_ids})

    def delete(self, *args):
        raise HTTPError(405)
