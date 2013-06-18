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
        print("URIs: PUT")
        raise HTTPError(405)

    @defer.inlineCallbacks
    def insert_in_both_tables(self, private_id, public_id):

        # Check whether this association already exists - choice of 200/201
        # status depends on this
        exists = False
        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=config.PUBLIC_IDS_TABLE,
                                            start=public_id,
                                            finish=public_id)

        for column in db_data:
            if column.column.name == public_id:
                exists = True

        if exists:
            self.set_status(httplib.OK)
        else:
            # check that neither pri nor public ID is at limit of allowed associations
            db_data = yield self.cass.get_slice(key=private_id,
                                                column_family=config.PUBLIC_IDS_TABLE)

            if len(db_data) >= config.MAX_ASSOCIATED_PUB_IDS:
                raise HTTPError(400, "", {"reason":"Associated Public Identity limit reached"})

            db_data = yield self.cass.get_slice(key=public_id,
                                                column_family=config.PRIVATE_IDS_TABLE)

            if len(db_data) >= config.MAX_ASSOCIATED_PRI_IDS:
                raise HTTPError(400, "", {"reason":"Associated Private Identity limit reached"})

            yield self.cass.insert(column_family=config.PUBLIC_IDS_TABLE,
                                   key=private_id,
                                   column=public_id,
                                   value=public_id)
            try:
                yield self.cass.insert(column_family=config.PRIVATE_IDS_TABLE,
                                       key=public_id,
                                       column=private_id,
                                       value=private_id)
            except:
                yield self.cass.remove(column_family=config.PUBLIC_IDS_TABLE,
                                       key=private_id,
                                       column=public_id,
                                       value=public_id)

            self.set_status(httplib.CREATED)

    @defer.inlineCallbacks
    def delete_from_both_tables(self, private_id, public_id):
        yield self.cass.remove(column_family=config.PUBLIC_IDS_TABLE, key=private_id, column=public_id)
        yield self.cass.remove(column_family=config.PRIVATE_IDS_TABLE, key=public_id, column=private_id)


class AssociatedPrivateHandler(AssociatedURIsHandler):
    """
    Handler for AssociatedPrivate - GET/POST/DELETE to query/add/remove
    private IDs associated to a public ID.

    """
    @defer.inlineCallbacks
    def get(self, public_id, private_id=None):
        print("PRI URIs: GET Priv: %s, Pub ID: %s" % (private_id, public_id))
        if private_id is not None or public_id is None:
            raise HTTPError(400)

        db_data = yield self.cass.get_slice(key=public_id,
                                            column_family=self.table)

        private_ids = []
        for column in db_data:
            private_ids.append(column.column.value)

        if private_ids == []:
            # Note: The get_slice API does not throw a NotFoundException if it
            # finds no matches
            raise HTTPError(404)

        self.finish({"public_id": public_id, "private_ids": private_ids})


    @defer.inlineCallbacks
    def post(self, public_id, private_id=None):
        print("PRI URIs: POST Priv: %s, Pub: %s" % (private_id, public_id))

        if private_id is not None or public_id is None:
            raise HTTPError(405)
        else:
            private_id = self.request.body
            if private_id == "":
                raise HTTPError(405)

        yield self.insert_in_both_tables(private_id, public_id)

        # Retrieve the updated full list of public IDs associated with this private ID
        db_data = yield self.cass.get_slice(key=public_id,
                                            column_family=self.table)
        private_ids = []
        for column in db_data:
            private_ids.append(column.column.value)

        self.finish({"public_id": public_id, "private_ids": private_ids})

    @defer.inlineCallbacks
    def delete(self, public_id, private_id=None):
        print("PRI URIs: DELETE Priv: %s Pub %s" % (private_id, public_id))
        if public_id is None:
            raise HTTPError(405)

        if private_id is not None:
            yield self.delete_from_both_tables(private_id, public_id)
        else:
            db_data = yield self.cass.get_slice(key=public_id,
                                                column_family=self.table)

            for column in db_data:
                yield self.delete_from_both_tables(column.column.value, public_id)

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
        print("PUB URIs: GET Priv: %s, Pub ID: %s" % (private_id, public_id))
        if public_id is not None or private_id is None:
            raise HTTPError(400)

        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=self.table)

        public_ids = []
        for column in db_data:
            public_ids.append(column.column.value)
        if public_ids == []:
            raise HTTPError(404)

        self.finish({"private_id": private_id, "public_ids": public_ids})

    @defer.inlineCallbacks
    def post(self, private_id, public_id=None):
        print("PUB URIs: POST Priv: %s, Pub: %s" % (private_id, public_id))

        if public_id is not None or private_id is None:
            raise HTTPError(405)
        else:
            public_id = self.request.body
            if public_id == "":
                raise HTTPError(405)

        yield self.insert_in_both_tables(private_id, public_id)

        # Retrieve the updated full list of public IDs associated with this private ID
        db_data = yield self.cass.get_slice(key=private_id,
                                            column_family=self.table)
        public_ids = []
        for column in db_data:
            public_ids.append(column.column.value)

        self.finish({"private_id": private_id, "public_ids": public_ids})


    @defer.inlineCallbacks
    def delete(self, private_id, public_id=None):
        print("PUB URIs: DELETE Priv: %s Pub %s" % (private_id, public_id))
        if private_id is None:
            raise HTTPError(405)

        if public_id is not None:
            yield self.delete_from_both_tables(private_id, public_id)
        else:
            db_data = yield self.cass.get_slice(key=private_id,
                                                column_family=self.table)
            for column in db_data:
                yield self.delete_from_both_tables(private_id, column.column.value)

        self.set_status(httplib.NO_CONTENT)
        self.finish()

