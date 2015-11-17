#!/usr/share/clearwater/crest/env/bin/python

# @file bulk_autocomplete.py
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
USAGE = """\
Metaswitch Clearwater bulk-provisioning autocompletion tool

This script must be run on a Homestead node.

This script takes a CSV file containing incomplete user information and
autocompletes it with sensible defaults.

Usage: bulk_create.py <csv file>

Each row in the input CSV file describes a user, and must contain 1-4
columns:
- public SIP ID (required)
- private SIP ID (optional, defaults to public SIP ID, stripping any sip:)
- realm (optional, defaults to system default)
- password (optional, defaults to auto-generated random password)

The script generates an output CSV file containing all 4 columns for each
user.  You can then pass this CSV file to bulk_create.py to generate scripts
to bulk-provision these users.
"""

import sys, string, csv, traceback
from metaswitch.common import utils

def standalone():
    if len(sys.argv) != 2:
        print USAGE
        return
    in_filename = sys.argv[1]
    in_filename_prefix = string.replace(in_filename, ".csv", "")
    out_filename = "%s.auto.csv" % (in_filename_prefix,)
    print "Autocompleting bulk provisioning users in %s..." % (in_filename,)
    try:
        with open(in_filename, 'rb') as in_file:
            with open(out_filename, 'w') as out_file:
                csv_reader = csv.reader(in_file)
                csv_writer = csv.writer(out_file)
                for row in csv_reader:
                    if len(row) == 1:
                        # Default private SIP ID to public SIP ID, stripping any sip: prefix
                        row.append(utils.sip_public_id_to_private(row[0]))
                    if len(row) == 2:
                        # Default realm to domain of public SIP ID
                        row.append(utils.sip_uri_to_domain(row[0]))
                    if len(row) == 3:
                        # Missing password - generate a random one
                        row.append(utils.create_secure_human_readable_id(48))
                    csv_writer.writerow(row)
        print "Autocompleted bulk provisioning users written to %s" % (out_filename,)
    except IOError as e:
        print "Failed to read/write to %s:" % (e.filename,)
        traceback.print_exc();

if __name__ == '__main__':
    standalone()
