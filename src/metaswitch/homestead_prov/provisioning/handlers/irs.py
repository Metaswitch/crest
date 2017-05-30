# @file irs.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

from twisted.internet import defer
from telephus.cassandra.ttypes import NotFoundException
from metaswitch.crest.api.base import BaseHandler

from ..models import PrivateID, IRS

JSON_PUBLIC_IDS = "public_ids"
JSON_PRIVATE_IDS = "private_ids"


class AllIRSHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def post(self):
        irs_uuid = yield IRS.create()
        self.set_header("Location", "/irs/%s" % irs_uuid)
        self.set_status(201)
        self.finish()


class IRSHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def delete(self, irs_uuid):
        try:
            yield IRS(irs_uuid).delete()
            self.finish()
        except NotFoundException:
            self.send_error(204)


class IRSAllPublicIDsHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, irs_uuid):
        try:
            ids = yield IRS(irs_uuid).get_associated_publics()
            self.send_json({JSON_PUBLIC_IDS: ids})
        except NotFoundException:
            self.send_error(404)


class IRSAllPrivateIDsHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self, irs_uuid):
        try:
            ids = yield IRS(irs_uuid).get_associated_privates()
            self.send_json({JSON_PRIVATE_IDS: ids})
        except NotFoundException:
            self.send_error(404)


class IRSPrivateIDHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def put(self, irs_uuid, private_id):
        try:
            # Associating the IRS with the private ID also does the reciprocal
            # association.
            yield PrivateID(private_id).associate_irs(irs_uuid)
            self.finish()
        except NotFoundException:
            self.send_error(404)

    @BaseHandler.requires_empty_body
    @defer.inlineCallbacks
    def delete(self, irs_uuid, private_id):
        try:
            # Dissociating the IRS with the private ID also does the reciprocal
            # association.
            yield PrivateID(private_id).dissociate_irs(irs_uuid)
            self.finish()
        except NotFoundException:
            self.send_error(404)
