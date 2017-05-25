#!/usr/share/clearwater/crest-prov/env/bin/python

# @file prepare_csv.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

#

import sys, string, csv, traceback, uuid
from metaswitch.common import utils
from metaswitch.common import ifcs, simservs
from metaswitch.crest.tools.utils import create_imssubscription_xml

SIMSERVS = simservs.default_simservs()

USAGE = """
Usage: prepare_csv.py <csv_file>

<csv_file> - A CSV file in the format:
             <public_id>,<private_id>,<realm>,<password>

Converts the given CSV file (which can be generated with bulk_autocomplete)
into a CSV file ready to be passed to BulkProvision to create SSTables.
"""

def standalone():
    if len(sys.argv) != 2:
        print USAGE
        return
    csv_filename = sys.argv[1]
    csv_filename_prefix = string.replace(csv_filename, ".csv", "")
    output_filename = "%s_prepared.csv" % (csv_filename_prefix)
    print "Preparing %s for bulk provisioning..." % (csv_filename)
    try:
        with open(csv_filename, 'rb') as csv_file, \
             open(output_filename, 'w') as output_file:

            reader = csv.reader(csv_file)
            for row in reader:
                if len(row) >= 4:
                    [public_id, private_id, realm, password] = row[0:4]

                    # Hash the password and generate the IMSSubscriptionXML.
                    hash = utils.md5("%s:%s:%s" % (private_id, realm, password))
                    publicidentity_xml = "<PublicIdentity><BarringIndication>1</BarringIndication><Identity>%s</Identity></PublicIdentity>" % public_id
                    initial_filter_xml = ifcs.generate_ifcs(utils.sip_uri_to_domain(public_id))
                    ims_subscription_xml = create_imssubscription_xml(private_id, publicidentity_xml, initial_filter_xml)
                    irs_uuid = uuid.uuid4();
                    sp_uuid = uuid.uuid4();

                    # Print a line for the user
                    output_file.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (public_id, private_id, realm, hash, SIMSERVS, publicidentity_xml, initial_filter_xml, ims_subscription_xml, irs_uuid, sp_uuid, password))
                else:
                    print 'Error: row %s contains <4 entries - ignoring' % row

        print "Bulk provisioning input created"
        print "- BulkProvision homer %s" % (output_filename)
        print "- BulkProvision homestead-local %s" % (output_filename)
        print "- BulkProvision homestead-hss %s" % (output_filename)
    except IOError as e:
        print "Failed to read/write to %s:" % (e.filename,)
        traceback.print_exc();

if __name__ == '__main__':
    standalone()
