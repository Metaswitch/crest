# @file private.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import logging
import json

from twisted.internet import defer
from telephus.cassandra.ttypes import NotFoundException
from metaswitch.crest import settings
from metaswitch.crest.api.base import BaseHandler
from ..models import PrivateID
from metaswitch.common import utils

_log = logging.getLogger("crest.api.homestead.cache")

JSON_DIGEST_HA1 = "digest_ha1"
JSON_PLAINTEXT_PASSWORD = "plaintext_password"
JSON_REALM = "realm"
JSON_ASSOC_IRS = "associated_implicit_registration_sets"
JSON_ASSOC_PUBLIC_IDS = "associated_public_ids"


class PrivateHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, private_id):
        try:
            (digest_ha1, plaintext_password, realm) = yield PrivateID(private_id).get_digest()
            body = {JSON_DIGEST_HA1: digest_ha1, JSON_REALM: realm}

            if plaintext_password != "":
                body[JSON_PLAINTEXT_PASSWORD] = plaintext_password

            self.send_json(body)

        except NotFoundException:
            self.send_error(404)

    @defer.inlineCallbacks
    def put(self, private_id):
        body = self.request.body
        if body:
            try:
                obj = json.loads(body)
            except ValueError:
                self.send_error(400, "Invalid JSON")
                return

            # There must be a digest_ha1 or plaintext_password (not both)
            # and there may be a realm
            plaintext_password = obj.get(JSON_PLAINTEXT_PASSWORD)
            digest_ha1 = obj.get(JSON_DIGEST_HA1)
            realm = obj.get(JSON_REALM) or settings.SIP_DIGEST_REALM

            if plaintext_password:
                # If there's a password then there mustn't be a digest.
                # Calculate the digest from the password
                if digest_ha1:
                    self.send_error(400, "Invalid JSON - both digest_ha1 and plaintext_password present")
                    return
                else:
                    digest_ha1 = utils.md5("%s:%s:%s" % (private_id,
                                                         realm,
                                                         plaintext_password))
            elif not digest_ha1:
                # There must be either the password or the digest
                self.send_error(400, "Invalid JSON - neither digest_ha1 and plaintext_password present")
                return
            else:
                # Set the password to the empty string if it's not set so
                # that we can store this in Cassandra. We have to do this
                # so that we can invalidate passwords when we receive a
                # PUT that contains a digest.
                plaintext_password = ""

            yield PrivateID(private_id).put_digest(digest_ha1,
                                                   plaintext_password,
                                                   realm)
            self.finish()

        else:
            self.send_error(400, "Empty body")

    @defer.inlineCallbacks
    def delete(self, private_id):
        try:
            yield PrivateID(private_id).delete()
            self.finish()
        except NotFoundException:
            self.send_error(204)


class PrivateAllIrsHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, private_id):
        try:
            irses = yield PrivateID(private_id).get_irses()
            self.send_json({JSON_ASSOC_IRS: irses})

        except NotFoundException:
            self.send_error(404)


class PrivateOneIrsHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def put(self, private_id, irs_uuid):
        try:
            yield PrivateID(private_id).associate_irs(irs_uuid)
            self.finish()
        except NotFoundException:
            self.send_error(404)

    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def delete(self, private_id, irs_uuid):
        try:
            yield PrivateID(private_id).dissociate_irs(irs_uuid)
            self.finish()
        except NotFoundException:
            self.send_error(204)


class PrivateAllPublicIdsHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, private_id):
        try:
            public_ids = yield PrivateID(private_id).get_public_ids()
            self.send_json({JSON_ASSOC_PUBLIC_IDS: public_ids})
        except NotFoundException:
            self.send_error(404)
