# @file service_profile.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

from twisted.internet import defer
from telephus.cassandra.ttypes import NotFoundException
from metaswitch.crest.api.base import BaseHandler
import xml.etree.ElementTree as ET

from ..models import PublicID, ServiceProfile

JSON_PUBLIC_IDS = "public_ids"


def verify_relationships(start=None, finish=None):
    """
    Decorator that verifies that an IRS, service profile, and public ID are all
    part of the same heirarchy.

    This assumes that the first parameter is a handler object, and the
    subsequent parameters are:
    -  IRS.
    -  service profile.
    -  public ID.

    The start and finish parameters are slice boundaries and specify which
    subsequent parameters to check.  For example:

    Checks that the service profile is a child of the IRS:
        @verify_relationships()
        def func1(self, irs_uuid, sp_uuid)

    Check that the service profile a child of the IRS, but does not check the
    public ID is a child of the service profile:
        @verify_relationships(finish=-1)
        def func2(self, irs_uuid, sp_uuid, private_id)
    """
    def decorator(func):
        @defer.inlineCallbacks
        def wrapper(handler, *pos_args):
            try:
                # Extract arguments.  The call to verify_relationships specifies
                # the slice of arguments to check.
                args_to_check = pos_args[start:finish]
                irs_uuid = sp_uuid = public_id = None

                try:
                    irs_uuid = args_to_check[0]
                    sp_uuid = args_to_check[1]
                    public_id = args_to_check[2]
                except IndexError:
                    pass

                # If we've got a service profile, check it's a child of the IRS.
                if sp_uuid:
                    parent_irs_uuid = yield ServiceProfile(sp_uuid).get_irs()
                    if irs_uuid != parent_irs_uuid:
                        handler.send_error(
                                403, "Service Profile not a child of IRS")
                        defer.returnValue(None)

                # If we've got a public ID, check it's a child of the service
                # profile.
                if public_id:
                    parent_sp_uuid = yield PublicID(public_id).get_sp()
                    if sp_uuid != parent_sp_uuid:
                        handler.send_error(
                                403, "Public ID not a child of Service Profile")
                        defer.returnValue(None)

                # All is well.  Actually call the underlying function.
                retval = yield func(handler, *pos_args)
                defer.returnValue(retval)

            except NotFoundException:
                # If we couldn't find a child object we were asked to check,
                # just return a 404 immediately.
                handler.send_error(404)

        return wrapper
    return decorator


class AllServiceProfilesHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @verify_relationships()
    @defer.inlineCallbacks
    def post(self, irs_uuid):
        sp_uuid = yield ServiceProfile.create(irs_uuid)
        self.set_header("Location", "/irs/%s/service_profiles/%s" %
                                                            (irs_uuid, sp_uuid))
        self.set_status(201)
        self.finish()


class ServiceProfileHandler(BaseHandler):
    @BaseHandler.requires_empty_body
    @verify_relationships()
    @defer.inlineCallbacks
    def delete(self, irs_uuid, sp_uuid):
        yield ServiceProfile(sp_uuid).delete()
        self.finish()


class SPAllPublicIDsHandler(BaseHandler):
    @verify_relationships()
    @defer.inlineCallbacks
    def get(self, irs_uuid, sp_uuid):
        try:
            public_ids = yield ServiceProfile(sp_uuid).get_public_ids()
            self.send_json({JSON_PUBLIC_IDS: public_ids})
        except NotFoundException:
            self.send_error(404)


class SPPublicIDHandler(BaseHandler):
    @verify_relationships(finish=-1)  # The public ID need not exist already.
    @defer.inlineCallbacks
    def put(self, irs_uuid, sp_uuid, public_id):
        try:
            # Check the public identity specified in the XML document matches
            # the public identity specified in the URL being PUT to.
            xml = self.request.body
            xml_root = ET.fromstring(xml)
            xml_public_id = xml_root.find("Identity").text

            if public_id == xml_public_id:
                yield PublicID(public_id).put_publicidentity(xml, sp_uuid)
                yield ServiceProfile(sp_uuid).associate_public_id(public_id)
            else:
                self.send_error(403, "Incorrect XML Identity")
        except ET.ParseError:
            self.send_error(400, "Badly formed XML: (%s)" % xml)

    @verify_relationships()
    @defer.inlineCallbacks
    def delete(self, irs_uuid, sp_uuid, public_id):
        try:
            yield PublicID(public_id).delete()
            self.finish()
        except NotFoundException:
            self.send_error(204)


class SPFilterCriteriaHandler(BaseHandler):
    @verify_relationships()
    @defer.inlineCallbacks
    def get(self, irs_uuid, sp_uuid):
        try:
            ifc = yield ServiceProfile(sp_uuid).get_ifc()
            self.write(ifc)
            self.finish()
        except NotFoundException:
            self.send_error(404)

    @verify_relationships()
    @defer.inlineCallbacks
    def put(self, irs_uuid, sp_uuid):
        xml_body = self.request.body

        if self.request.body:
            yield ServiceProfile(sp_uuid).update_ifc(xml_body)
        else:
            self.send_error(400, "Body is empty")
