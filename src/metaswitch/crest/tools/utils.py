# @file utils.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import xml.etree.ElementTree as ET
import random, datetime, StringIO

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
    xml = output.getvalue().replace('\n','')

    return xml

def create_answered_call_list_entries(uri, outgoing, timestamp):
    """
    Create the fragments for an answered call. This consists of two XML-like
    fragments: a begin record and an end record.

    @param uri       - The URI that owns the call list.
    @param outgoing  - Whether this was an outgoing (as opposed to incoming) call.
    @param timestamp - The time the call was made.
    """

    # Create a complete call list entry. This returns a valid XML document
    # enclosed in a <call> tag.
    entry = create_full_call_list_entry(uri, outgoing, True, timestamp)

    # Remove the outer <call> tag and split the record in two.  The <end-time>
    # part goes in the end fragment, everything else in the begin fragment.
    entry = entry.replace("<call>", "").replace("</call>", "")
    parts = entry.partition('<end-time>')
    return parts[0], parts[1] + parts[2]

def create_rejected_call_list_entry(uri, outgoing, timestamp):
    """
    Create the call list fragment for a rejected call.

    This is formed of the complete call list entry XML document, with the outer
    <call> tags removed.

    @param uri       - The URI that owns the call list.
    @param outgoing  - Whether this was an outgoing (as opposed to incoming) call.
    @param timestamp - The time the call was made.
    """
    full_entry = create_full_call_list_entry(uri, outgoing, False, timestamp)
    return full_entry.replace("<call>", "").replace("</call>", "")

def create_full_call_list_entry(uri, outgoing, answered, timestamp):
    """
    Create a complete call list entry XML document.

    @param uri       - The URI that owns the call list.
    @param outgoing  - Whether this was an outgoing (as opposed to incoming) call.
    @param outgoing  - Whether this was answered.
    @param timestamp - The time the call was made.

    The document is of the form:

        <call>
          <to>
            <URI>alice@example.com</URI>
            <name>Alice Adams</name> <!-- If present -->
          </to>
          <from>
            <URI>bob@example.com</URI>
            <name>Bob Barker</name>  <!-- If present -->
          </from>
          <answered>1</answered>
          <outgoing>1</outgoing>
          <start-time>2002-05-30T09:30:10</start-time> <!-- Standard XML DateTime type -->
          <answer-time>2002-05-30T09:30:20</answer-time> <!-- Present iff call was answered-->
          <end-time>2002-05-30T09:35:00</end-time> <!-- Present iff call was answered-->
        </call>

    """

    call_elem = ET.Element('call')

    if outgoing:
        call_elem.append(local_identity(uri, 'from'))
        call_elem.append(remote_identity('to'))
    else:
        call_elem.append(local_identity(uri, 'to'))
        call_elem.append(remote_identity('from'))

    answered_elem = ET.SubElement(call_elem, 'answered')
    answered_elem.text = '1' if answered else '0'

    outgoing_elem = ET.SubElement(call_elem, 'outgoing')
    outgoing_elem.text = '1' if outgoing else '0'

    start_time_elem = ET.SubElement(call_elem, 'start-time')
    start_time_elem.text = call_list_timestamp(timestamp)

    if answered:
        answered_time_elem = ET.SubElement(call_elem, 'answered-time')
        answered_time_elem.text = call_list_timestamp(timestamp + 10)

        end_time_elem = ET.SubElement(call_elem, 'end-time')
        end_time_elem.text = call_list_timestamp(timestamp + 60)

    return ET.tostring(call_elem)

def call_list_timestamp(timestamp):
    """
    Format a timestamp (in seconds since the epoch) into the XML encoding.
    """
    return datetime.datetime.utcfromtimestamp(timestamp).isoformat()

def local_identity(uri, tag):
    """
    Create an XML element representing the "local" identity (i.e. the owner of
    the call list).
    """
    top_elem = ET.Element(tag)
    uri_elem = ET.SubElement(top_elem, "URI")
    # Omit the name element (as it would often not be present in the underlying
    # SIP signaling).
    uri_elem.text = uri
    return top_elem

def remote_identity(tag):
    """
    Create an XML element representing the "remote" identity (i.e. the party the
    call list owner called or was called by).  We choose a random URI that looks
    like a DN.
    """
    top_elem = ET.Element(tag)
    uri_elem = ET.SubElement(top_elem, "URI")
    name_elem = ET.SubElement(top_elem, "name")

    number = "%0.10d" % random.randrange(10000000000)
    uri_elem.text = "sip:%s@example.com" % number
    name_elem.text = "Tel number %s" % number

    return top_elem
