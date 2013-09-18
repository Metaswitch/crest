#!/usr/share/clearwater/homestead/env/bin/python

# @file bulk_create.py
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
Metaswitch Clearwater bulk-provisioning script creation tool

This script must be run on a Homestead node.

This script generates two output scripts and two configuration files that
provision the Homestead and Homer (XDM) deployments.

Usage: bulk_create.py <csv file>

Each row in the input CSV file describes a user, and must contain 4 columns:
- public SIP ID
- private SIP ID
- realm
- password
If you have a CSV file with fewer columns, you can autocomplete the remaining
columns using the bulk_autocomplete.py script.
"""

import sys, string, csv, os, stat
from metaswitch.crest import settings
from metaswitch.common import utils
from metaswitch.common import ifcs

INITIAL_FILTER_CRITERIA = ifcs.generate_ifcs(settings.SIP_DIGEST_REALM)
with open(settings.XDM_DEFAULT_SIMSERVS_FILE, "rb") as simservs_file:
    SIMSERVS = simservs_file.read()

def standalone():
    if len(sys.argv) != 2:
        print USAGE
        return
    csv_filename = sys.argv[1]
    csv_filename_prefix = string.replace(csv_filename, ".csv", "")
    homestead_filename = "%s.create_homestead.sh" % (csv_filename_prefix,)
    homestead_casscli_filename = "%s.create_homestead.casscli" % (csv_filename_prefix,)
    xdm_filename = "%s.create_xdm.sh" % (csv_filename_prefix,)
    xdm_cqlsh_filename = "%s.create_xdm.cqlsh" % (csv_filename_prefix,)
    print "Generating bulk provisioning scripts for users in %s..." % (csv_filename,)
    try:
        with open(csv_filename, 'rb') as csv_file, \
             open(homestead_filename, 'w') as homestead_file, \
             open(homestead_casscli_filename, 'w') as homestead_casscli_file, \
             open(xdm_filename, 'w') as xdm_file, \
             open(xdm_cqlsh_filename, 'w') as xdm_cqlsh_file:
            # Write Homestead/CQL header
            homestead_file.write("#!/bin/bash\n")
            homestead_file.write("# Homestead bulk provisioning script for users in %s\n" % (csv_filename,))
            homestead_file.write("# Run this script on any node in your Homestead deployment to create the users\n")
            homestead_file.write("# The %s file must also be present on this system\n" % (homestead_casscli_filename,))
            homestead_file.write("# You must also run %s on any node in your Homer deployment\n" % (xdm_filename,))
            homestead_file.write("\n")
            homestead_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (homestead_casscli_filename, homestead_casscli_filename))
            homestead_file.write("cassandra-cli -B -f %s\n" % (homestead_casscli_filename,))
            homestead_casscli_file.write("USE homestead;\n");

            # Write Homer/CQL header
            xdm_file.write("#!/bin/bash\n")
            xdm_file.write("# Homer bulk provisioning script for users in %s\n" % (csv_filename,))
            xdm_file.write("# Run this script on any node in your Homer deployment to create the users\n")
            xdm_file.write("# The %s file must also be present on this system\n" % (xdm_cqlsh_filename,))
            xdm_file.write("# You must also run %s on any node in your Homestead deployment\n" % (homestead_filename,))
            xdm_file.write("\n")
            xdm_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (xdm_cqlsh_filename, xdm_cqlsh_filename))
            xdm_file.write("cqlsh -3 -f %s\n" % (xdm_cqlsh_filename,))
            xdm_cqlsh_file.write("USE homer;\n")

            reader = csv.reader(csv_file)
            for row in reader:
                if len(row) >= 4:
                    [public_id, private_id, realm, password] = row[0:4]

                    # Hash and then encrypt the password.
                    hash = utils.md5("%s:%s:%s" % (private_id, realm, password))
                    encrypted_hash = utils.encrypt_password(hash, settings.PASSWORD_ENCRYPTION_KEY)

                    # Add the user to the SIP digest, associated IDs and filter criteria tables on Homestead.
                    homestead_casscli_file.write("SET sip_digests['%s']['private_id'] = '%s';\n" % (private_id, private_id))
                    homestead_casscli_file.write("SET sip_digests['%s']['digest'] = '%s';\n" % (private_id, encrypted_hash))
                    homestead_casscli_file.write("SET public_ids['%s']['%s'] = '%s';\n" % (private_id, public_id, public_id))
                    homestead_casscli_file.write("SET private_ids['%s']['%s'] = '%s';\n" % (public_id, private_id, private_id))
                    homestead_casscli_file.write("SET filter_criteria['%s']['public_id'] = '%s';\n" % (public_id, public_id))
                    homestead_casscli_file.write("SET filter_criteria['%s']['value'] = '%s';\n" % (public_id, INITIAL_FILTER_CRITERIA))

                    # Add the simservs document for the user to the documents table  on Homer
                    xdm_cqlsh_file.write("INSERT INTO simservs (user, value) VALUES ('%s', '%s');\n" % (public_id, SIMSERVS))
                else:
                    print 'Error: row "%s" contains <4 entries - ignoring'

        # Make the created .sh files executable
        os.chmod(homestead_filename, stat.S_IEXEC)
        os.chmod(xdm_filename, stat.S_IEXEC)

        print "Generated bulk provisioning scripts written to"
        print "- %-46s - run this script on Homestead" % (homestead_filename,)
        print "- %-46s - copy this file onto Homestead" % (homestead_casscli_filename,)
        print "- %-46s - run this script on Homer" % (xdm_filename,)
        print "- %-46s - copy this file onto Homer" % (xdm_cqlsh_filename,)
    except IOError as e:
        print "Failed to read/write to %s:" % (e.filename,)
        traceback.print_exc();

if __name__ == '__main__':
    standalone()
