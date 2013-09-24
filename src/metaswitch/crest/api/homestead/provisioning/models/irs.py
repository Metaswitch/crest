# @file irs.py
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

import xml.etree.ElementTree as ET
import StringIO
import uuid

from twisted.internet import defer

from ... import config

from .db import ProvisioningModel
from .private import PrivateID
from .public import PublicID
from .service_profile import ServiceProfile

CREATED = "created"
ASSOC_PRIVATE_PREFIX = "associated_private_"
SERVICE_PROFILE_PREFIX = "service_profile_"


class IRS(ProvisioningModel):
    """Model representing an implicit registration set"""

    cass_table = config.IRS_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "id uuid PRIMARY KEY, " +
            CREATED+" boolean" +
        ") WITH read_repair_chance = 1.0;"
    )

    @classmethod
    @defer.inlineCallbacks
    def create(cls):
        irs_uuid = uuid.uuid4()
        IRS(irs_uuid).modify_columns({CREATED: True})
        defer.returnValue(irs_uuid)

    @defer.inlineCallbacks
    def get_associated_privates(self):
        retval = yield self.get_columns_with_prefix_stripped(ASSOC_PRIVATE_PREFIX)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_associated_service_profiles(self):
        retval = yield self.get_columns_with_prefix_stripped(SERVICE_PROFILE_PREFIX)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_associated_publics(self):
        sp_uuids = yield self.get_associated_service_profiles()

        public_ids = [(yield ServiceProfile(uuid).get_public_ids())
                                                           for uuid in sp_uuids]
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def associate_private_id(self, private_id):
        yield self.assert_row_exists()
        yield self.modify_columns({ASSOC_PRIVATE_PREFIX + private_id: None})

    @defer.inlineCallbacks
    def dissociate_private_id(self, private_id):
        yield self.delete_columns([ASSOC_PRIVATE_PREFIX + private_id])

    @defer.inlineCallbacks
    def associate_service_profile(self, sp_uuid):
        yield self.assert_row_exists()
        yield self.modify_columns({ASSOC_PRIVATE_PREFIX + str(sp_uuid): None})
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_service_profile(self, sp_uuid):
        yield self.delete_columns([ASSOC_PRIVATE_PREFIX + str(sp_uuid)])
        yield self.rebuild()

    @defer.inlineCallbacks
    def delete(self):
        sp_uuids = yield self.get_associated_service_profiles()
        for uuid in sp_uuids:
            yield ServiceProfile(uuid).delete()

        private_ids = yield self.get_associated_privates()
        for priv in private_ids:
            yield PrivateID(priv).dissociate_irs(self.row_key)

        self.delete_row()

    @defer.inlineCallbacks
    def build_imssubscription_xml(self):
        # Create an IMS subscription mode with a dummy private ID node.
        root = ET.Element("IMSSubscription")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xsi:noNamespaceSchemaLocation", "CxDataType.xsd")

        priv_elem = ET.SubElement(root, "PrivateID")
        priv_elem.text = "Unspecified"

        # Add a ServiceProfile node for each profile in this IRS.
        sp_uuids = yield self.get_associated_service_profiles()
        for sp_uuid in sp_uuids:
            sp_elem = ET.SubElement(root, "ServiceProfile")

            # Add the Initial Filer Criteria node for this profile.
            ifc_xml = yield ServiceProfile(sp_uuid).get_ifc()
            ifc_xml_elem = ET.fromstring(ifc_xml)
            sp_elem.append(ifc_xml_elem)

            # Add a PublicIdentity node for each ID in this service profile. The
            # contents of this node are stored in the database.
            public_ids = yield ServiceProfile(sp_uuid).get_public_ids()
            for pub_id in public_ids:
                pub_id_xml = yield PublicID(pub_id).get_publicidentity()
                pub_id_xml_elem = ET.fromstring(pub_id_xml)
                sp_elem.append(pub_id_xml_elem)

        # Generate the new IMS subscription XML document.
        output = StringIO.StringIO()
        tree = ET.ElementTree(root)
        tree.write(output)
        xml = output.getvalue()

        defer.returnValue(xml)

    @defer.inlineCallbacks
    def rebuild(self):
        """
        Rebuild the IMPI and IMPU tables in the cache when the IRS (or it's
        children are modified).
        """

        xml = yield self.build_imssubscription_xml()
        timestamp = self._cache.generate_timestamp()

        for pub_id in (yield self.get_associated_publics()):
            yield self._cache.put_ims_subscription(pub_id, xml, timestamp)

        for priv_id in (yield self.get_associated_privates()):
            yield PrivateID(priv_id).rebuild()
