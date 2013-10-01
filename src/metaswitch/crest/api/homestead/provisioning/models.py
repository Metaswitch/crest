# @file models.py
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
from telephus.cassandra.ttypes import NotFoundException

from .. import config
from metaswitch.crest.api import utils
from ..cassandra import CassandraModel

NULL_COLUMN_VALUE = ""

class ProvisioningModel(CassandraModel):
    cass_keyspace = config.PROVISIONING_KEYSPACE

    @classmethod
    def register_cache(cls, cache):
        cls._cache = cache

    @defer.inlineCallbacks
    def assert_row_exists(self):
        """Checks if the row exists and if not raise NotFoundException"""

        # To check if the row exists, simply try to read all it's columns.
        yield self.get_columns()

    @staticmethod
    def convert_uuid(this_uuid):
        """Convert a uuid in various formats to a byte array."""

        if isinstance(this_uuid, uuid.UUID):
            # UUID has been passed as a UUID object.  Convert it to bytes.
            return this_uuid.bytes
        elif isinstance(this_uuid, basestring):
            # UUID has been passed as a string.  It could either be a byte
            # array, or a string of the form 123456-1234-1234-1234-1234567890ab
            try:
                return uuid.UUID(this_uuid).bytes
            except ValueError:
                pass

            try:
                return uuid.UUID(bytes=this_uuid).bytes
            except ValueError:
                pass

        # Not got a valid UUID.
        raise ValueError("Row key must be a UUID or a byte array " +
                         "(got %s of type %s)" % (this_uuid, type(this_uuid)))


class IRS(ProvisioningModel):
    """Model representing an implicit registration set"""

    ASSOC_PRIVATE_PREFIX = "associated_private_"
    SERVICE_PROFILE_PREFIX = "service_profile_"

    cass_table = config.IRS_TABLE

    # Note that CQL requires at least one non-dynamic column (hence the use of
    # the "dummy" column below).
    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "id uuid PRIMARY KEY, " +
            "dummy text"
        ") WITH read_repair_chance = 1.0;"
    )

    def __init__(self, row_key):
        super(IRS, self).__init__(self.convert_uuid(row_key))

    @classmethod
    @defer.inlineCallbacks
    def create(cls):
        irs_uuid = uuid.uuid4()
        yield IRS(irs_uuid).touch()
        defer.returnValue(irs_uuid)

    @defer.inlineCallbacks
    def get_associated_privates(self):
        priv_hash = yield self.get_columns_with_prefix_stripped(self.ASSOC_PRIVATE_PREFIX)
        defer.returnValue(priv_hash.keys())

    @defer.inlineCallbacks
    def get_associated_service_profiles(self):
        sp_hash = yield self.get_columns_with_prefix_stripped(self.SERVICE_PROFILE_PREFIX)
        defer.returnValue(sp_hash.keys())

    @defer.inlineCallbacks
    def get_associated_publics(self):
        sp_uuids = yield self.get_associated_service_profiles()

        public_ids = utils.flatten(
			[(yield ServiceProfile(uuid).get_public_ids())
                         for uuid in sp_uuids])
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def associate_private_id(self, private_id):
        yield self.assert_row_exists()
        yield self.modify_columns({self.ASSOC_PRIVATE_PREFIX + private_id:
                                                            NULL_COLUMN_VALUE})

    @defer.inlineCallbacks
    def dissociate_private_id(self, private_id):
        yield self.delete_columns([self.ASSOC_PRIVATE_PREFIX + private_id])

    @defer.inlineCallbacks
    def associate_service_profile(self, sp_uuid):
        yield self.assert_row_exists()
        yield self.modify_columns({self.SERVICE_PROFILE_PREFIX + str(sp_uuid):
                                                            NULL_COLUMN_VALUE})
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_service_profile(self, sp_uuid):
        yield self.delete_columns([self.SERVICE_PROFILE_PREFIX + str(sp_uuid)])
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
            # Add the Initial Filer Criteria node for this profile. If not
            # present just ignore the profile entirely.
            try:
                ifc_xml = yield ServiceProfile(sp_uuid).get_ifc()
                ifc_xml_elem = ET.fromstring(ifc_xml)

                sp_elem = ET.SubElement(root, "ServiceProfile")
                sp_elem.append(ifc_xml_elem)

                # Add a PublicIdentity node for each ID in this service
                # profile. The contents of this node are stored in the
                # database.
                public_ids = yield ServiceProfile(sp_uuid).get_public_ids()
                for pub_id in public_ids:
                    pub_id_xml = yield PublicID(pub_id).get_publicidentity()
                    pub_id_xml_elem = ET.fromstring(pub_id_xml)
                    sp_elem.append(pub_id_xml_elem)

            except NotFoundException:
                pass

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


class PrivateID(ProvisioningModel):
    """Model representing a provisioned private ID"""

    DIGEST_HA1 = "digest_ha1"
    ASSOC_IRS_PREFIX = "associated_irs_"

    cass_table = config.PRIVATE_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "private_id text PRIMARY KEY, " +
            DIGEST_HA1+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_digest(self):
        digest = yield self.get_column_value(self.DIGEST_HA1)
        defer.returnValue(digest)

    @defer.inlineCallbacks
    def get_irses(self):
        irses_hash = \
            yield self.get_columns_with_prefix_stripped(self.ASSOC_IRS_PREFIX)
        defer.returnValue(irses_hash.keys())

    @defer.inlineCallbacks
    def get_public_ids(self):
        irs_uuids = yield self.get_irses()
        public_ids = utils.flatten((yield IRS(uuid).get_public_ids())
                                                          for uuid in irs_uuids)
        defer.returnValue(public_ids)

    @defer.inlineCallbacks
    def put_digest(self, digest):
        yield self.modify_columns({self.DIGEST_HA1: digest})
        yield self._cache.put_digest(self.row_key,
                                     digest,
                                     self._cache.generate_timestamp())

    @defer.inlineCallbacks
    def delete(self):
        irs_uuids = yield self.get_irses()
        for uuid in irs_uuids:
            yield IRS(uuid).dissociate_private_id(self.row_key)

        yield self.delete_row()
        yield self._cache.delete_private_id(self.row_key,
                                            self._cache.generate_timestamp())

    @defer.inlineCallbacks
    def associate_irs(self, irs_uuid):
        yield self.assert_row_exists()
        yield self.modify_columns({self.ASSOC_IRS_PREFIX + str(irs_uuid):
                                                            NULL_COLUMN_VALUE})
        yield IRS(irs_uuid).associate_private_id(self.row_key)
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_irs(self, irs_uuid):
        yield self.delete_columns([self.ASSOC_IRS_PREFIX + str(irs_uuid)])
        yield IRS(irs_uuid).dissociate_private_id(self.row_key)
        yield self.rebuild()

    @defer.inlineCallbacks
    def rebuild(self):
        """ Rebuild the IMPI table in the cache """

        # Get all the information we need to rebuild the cache.  Do this before
        # deleting any cache entries to minimize the time the cache is empty.
        digest = yield self.get_digest()

        public_ids = []
        for irs in (yield self.get_irses()):
            for pub_id in (yield IRS(irs).get_associated_publics()):
                public_ids.append(pub_id)

        timestamp = self._cache.generate_timestamp()

        # Delete the existing cache entry then write back the digest and the
        # associated public IDs.
        yield self._cache.delete_private_id(self.row_key, timestamp)
        yield self._cache.put_digest(self.row_key, digest, timestamp)
        for pub_id in public_ids:
            yield self._cache.put_associated_public_id(self.row_key,
                                                       pub_id,
                                                       timestamp)


class PublicID(ProvisioningModel):
    """Model representing a provisioned public identity"""

    SERVICE_PROFILE = "service_profile"
    PUBLICIDENTITY = "publicidentity"

    cass_table = config.PUBLIC_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "public_id text PRIMARY KEY, " +
            PUBLICIDENTITY+" text, " +
            SERVICE_PROFILE+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    @defer.inlineCallbacks
    def get_sp(self):
        sp_uuid = yield self.get_column_value(self.SERVICE_PROFILE)
        defer.returnValue(sp_uuid)

    @defer.inlineCallbacks
    def get_publicidentity(self):
        xml = yield self.get_column_value(self.PUBLICIDENTITY)
        defer.returnValue(xml)

    @defer.inlineCallbacks
    def get_irs(self):
        sp_uuid = yield self.get_sp()
        irs_uuid = yield ServiceProfile(sp_uuid).get_irs()
        defer.returnValue(irs_uuid)

    @defer.inlineCallbacks
    def get_private_ids(self):
        irs_uuid = yield self.get_irs()
        private_ids = yield IRS(irs_uuid).get_associated_privates()
        defer.returnValue(private_ids)

    @defer.inlineCallbacks
    def put_publicidentity(self, xml, sp_uuid):
        yield self.modify_columns({self.PUBLICIDENTITY: xml,
                                   self.SERVICE_PROFILE: sp_uuid})

    @defer.inlineCallbacks
    def delete(self):
        irs_uuid = yield self.get_irs()
        sp_uuid = yield self.get_sp()

        yield ServiceProfile(sp_uuid).dissociate_public_id(self.row_key)
        yield self.delete_row()
        yield self._cache.delete_public_id(self.row_key,
                                           self._cache.generate_timestamp())

        yield IRS(irs_uuid).rebuild()


class ServiceProfile(ProvisioningModel):
    """Model representing a provisioned service profile"""

    IRS_COLUMN = "irs"
    IFC_COLUMN = "initialfiltercriteria"
    PUBLIC_ID_COLUMN_PREFIX = "public_id_"

    cass_table = config.SP_TABLE

    cass_create_statement = (
        "CREATE TABLE "+cass_table+" (" +
            "id uuid PRIMARY KEY, " +
            IRS_COLUMN+" text, " +
            IFC_COLUMN+" text" +
        ") WITH read_repair_chance = 1.0;"
    )

    def __init__(self, row_key):
        super(ServiceProfile, self).__init__(self.convert_uuid(row_key))

    @classmethod
    @defer.inlineCallbacks
    def create(self, irs_uuid):
        sp_uuid = uuid.uuid4()
        yield ServiceProfile(sp_uuid).modify_columns(
                                            {self.IRS_COLUMN: str(irs_uuid)})
        yield IRS(irs_uuid).associate_service_profile(sp_uuid)
        defer.returnValue(sp_uuid)

    @defer.inlineCallbacks
    def get_public_ids(self):
        pub_hash = yield self.get_columns_with_prefix_stripped(
                                                self.PUBLIC_ID_COLUMN_PREFIX)
        defer.returnValue(pub_hash.keys())

    @defer.inlineCallbacks
    def get_ifc(self):
        retval = yield self.get_column_value(self.IFC_COLUMN)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def get_irs(self):
        retval = yield self.get_column_value(self.IRS_COLUMN)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def associate_public_id(self, public_id):
        yield self.assert_row_exists()
        yield self.modify_columns({self.PUBLIC_ID_COLUMN_PREFIX + public_id:
                                                            NULL_COLUMN_VALUE})
        yield self.rebuild()

    @defer.inlineCallbacks
    def dissociate_public_id(self, public_id):
        yield self.delete_column(self.PUBLIC_ID_COLUMN_PREFIX + public_id)
        yield self.rebuild()

    @defer.inlineCallbacks
    def update_ifc(self, ifc):
        yield self.assert_row_exists()
        yield self.modify_columns({self.IFC_COLUMN: ifc})
        yield self.rebuild()

    @defer.inlineCallbacks
    def delete(self):
        public_ids = yield self.get_public_ids()
        for pub_id in public_ids:
            yield PublicID(pub_id).delete()

        irs_uuid = yield self.get_irs()
        IRS(irs_uuid).dissociate_service_profile(self.row_key)

        self.delete_row()

    @defer.inlineCallbacks
    def rebuild(self):
        irs_uuid = yield self.get_irs()
        yield IRS(irs_uuid).rebuild()
