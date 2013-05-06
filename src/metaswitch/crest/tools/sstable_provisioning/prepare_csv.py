#!/usr/share/clearwater/homer/env/bin/python

# @file prepare_csv.py
#
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by post at
# Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK

#

import sys, string, csv
from metaswitch.crest import settings
from metaswitch.common import utils
from metaswitch.common import ifcs

INITIAL_FILTER_CRITERIA = ifcs.generate_ifcs(settings.SIP_DIGEST_REALM)
with open(settings.XDM_DEFAULT_SIMSERVS_FILE, "rb") as simservs_file:
    SIMSERVS = simservs_file.read()
SIMSERVS = SIMSERVS.rstrip()

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

                    # Hash and then encrypt the password.
                    hash = utils.md5("%s:%s:%s" % (private_id, realm, password))
                    encrypted_hash = utils.encrypt_password(hash, settings.PASSWORD_ENCRYPTION_KEY)

                    output_file.write("%s,%s,%s,%s,%s\n" % (public_id, private_id, encrypted_hash, SIMSERVS, INITIAL_FILTER_CRITERIA))
                else:
                    print 'Error: row "%s" contains <4 entries - ignoring'

        print "Bulk provisioning input created"
        print "- BulkProvision %s homer" % (output_filename)
        print "- BulkProvision %s homestead" % (output_filename)
    except IOError as e:
        print "Failed to read/write to %s:" % (e.filename,)
        traceback.print_exc();

if __name__ == '__main__':
    standalone()
