#!/usr/share/clearwater/crest-prov/env/bin/python

# @file bulk_autocomplete.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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
