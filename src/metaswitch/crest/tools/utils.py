# @file utils.py
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

def create_imssubscription_xml(private_id, publicidentity_xml, ifc_xml):
    """
    Create an IMS subscription document containing one private identity, one
    public identity, and some IFCs.

    The IFC XML may contain multiple IFCs. They must all be enclosed in a
    <ServiceProfile> tag. In addition the XML may be a complete document with an
    XML header. For example:

    <?xml version="1.0" encoding="UTF-8"?>
    <ServiceProfile>
      <InitialFilterCriteria>...</InitialFilterCriteria>
      <InitialFilterCriteria>...</InitialFilterCriteria>
    </ServiceProfile>

    This method is closely related to IRS.build_imssubscription_xml. They should
    be kept in sync. (TODO: refactor these into one method).
    """

    root = ET.Element("IMSSubscription")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "CxDataType.xsd")

    # Add the private ID element.
    priv_elem = ET.SubElement(root, "PrivateID")
    priv_elem.text = private_id

    # Create a service profile element (which contains the IFCs) and append the
    # public identity to it.
    sp_elem = ET.fromstring(ifc_xml)
    pub_elem = ET.fromstring(publicidentity_xml)
    sp_elem.append(pub_elem)

    # Append the ServiceProfile to the IMS subscription.
    root.append(sp_elem)

    output = StringIO.StringIO()
    tree = ET.ElementTree(root)
    tree.write(output, encoding="UTF-8", xml_declaration=True)
    xml = output.getvalue()

    return xml
