#!/usr/share/clearwater/crest/env/bin/python

# @file prepare_csv.py
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
