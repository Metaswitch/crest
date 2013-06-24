# @file credentials.py
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
from metaswitch.crest.api.homestead.hss.gateway import HSSNotFound
from metaswitch.crest.api.homestead import config

_log = logging.getLogger("crest.api.homestead")

class PrivateCredentialsHandler(PassthroughHandler):
    """
    Handler for Credentials

    """
    @defer.inlineCallbacks
    def get(self, private_id):
        try:
            encrypted_hash = yield self.cass.get(column_family=self.table,
                                                 key=private_id,
                                                 column=self.column)
            digest = utils.decrypt_password(encrypted_hash.column.value,
                                            settings.PASSWORD_ENCRYPTION_KEY)
        except NotFoundException, e:
            raise HTTPError(httplib.NOT_FOUND)
            # Clearwater doesn't support an HSS lookup for credentials on this
            # interface.  The only time we should get a request for credentials
            # with just a privateID is from restund, and by that point the
            # local database should already have been populated by an earlier
            # query on the AssociatedCredentials API from sprout.

        self.finish({"digest": digest})

    @defer.inlineCallbacks
    def put(self, private_id):
        response = {}

        pw_hash = self.request_data.get("digest", None)
        encrypted_hash = utils.encrypt_password(pw_hash, settings.PASSWORD_ENCRYPTION_KEY)

        yield self.cass.insert(column_family=self.table,
                               key=private_id,
                               column=self.column,
                               value=encrypted_hash)

        self.finish(response)

    @defer.inlineCallbacks
    def delete(self, private_id):
        yield self.cass.remove(column_family=self.table, key=private_id, column=self.column)
        self.set_status(httplib.NO_CONTENT)
        self.finish()

    def post(self, *args):
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)


class AssociatedCredentialsHandler(PassthroughHandler):
    """
    Handler for getting Credentials, & confirming associated public ID.

    """
    @defer.inlineCallbacks
    def get(self, private_id, public_id):
        try:
            exists = False
            db_data = yield self.cass.get_slice(key=private_id,
                                                column_family=config.PUBLIC_IDS_TABLE,
                                                start=public_id,
                                                finish=public_id)
            for column in db_data:
                if column.column.name == public_id:
                    exists = True
            if not exists:
                raise NotFoundException()
            encrypted_hash = yield self.cass.get(column_family=self.table,
                                                 key=private_id,
                                                 column=self.column)
            digest = utils.decrypt_password(encrypted_hash.column.value,
                                            settings.PASSWORD_ENCRYPTION_KEY)
        except NotFoundException, e:
            if not settings.HSS_ENABLED:
                raise HTTPError(httplib.NOT_FOUND)

            # Either the digest or the association doesn't exist in the DB, attempt an
            # import from the HSS
            try:
                digest = yield self.application.hss_gateway.get_digest(private_id, public_id)
                public_ids = yield self.application.hss_gateway.get_public_ids(private_id, public_id)
            except HSSNotFound, e:
                raise HTTPError(httplib.NOT_FOUND)
            # Have result from HSS, store in Cassandra
            encrypted_hash = utils.encrypt_password(digest, settings.PASSWORD_ENCRYPTION_KEY)
            # yield self.cass.insert(column_family=self.table,
            #                        key=private_id,
            #                        column=self.column,
            #                        value=encrypted_hash)
            _log.info("Got associated publics: %s" % public_ids)

        self.finish({"digest": digest})

    def post(self, private_id, public_id=None):
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)

    def delete(self, private_id, public_id=None):
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)

    def put(self, *args):
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)
