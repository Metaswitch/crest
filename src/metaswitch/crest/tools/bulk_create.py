#!/usr/share/clearwater/crest/env/bin/python

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

import string, csv, os, stat, uuid, traceback, random, time, argparse

from metaswitch.common import utils
from metaswitch.common import ifcs, simservs
from metaswitch.crest.tools.utils import create_imssubscription_xml, create_answered_call_list_entries, create_rejected_call_list_entry

SIMSERVS = simservs.default_simservs()

# The number of call list entries to create
CALL_LIST_NUM_CALLS = 150

# The time range over which to spread the call lists (1 week).
CALL_LIST_TIME_RANGE_S = 1 * 7 * 24 * 60 * 60


def csv_iterator(csv_filename):
    '''
    Utility method to iterate over the rows in the input CSV file
    '''
    with open(csv_filename, 'rb') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) >= 4:
                yield row[0:4]
            else:
                print 'Error: row "%s" contains <4 entries - ignoring'


def create_row_command(table, row_key):
    """
    Utility function that writes a row into a homestead keyspace with the
    required "_exists" field
    """
    return "SET %s['%s']['_exists'] = '';\n" % (table, row_key)


def write_homestead_scripts(csv_filename, write_plaintext_password):
    csv_filename_prefix = string.replace(csv_filename, ".csv", "")
    homestead_filename = "%s.create_homestead.sh" % (csv_filename_prefix)
    homestead_prov_casscli_filename = "%s.create_homestead_provisioning.casscli" % (csv_filename_prefix)
    homestead_cache_casscli_filename = "%s.create_homestead_cache.casscli" % (csv_filename_prefix)

    with open(homestead_filename, 'w') as homestead_file, \
         open(homestead_cache_casscli_filename, 'w') as homestead_cache_casscli_file, \
         open(homestead_prov_casscli_filename, 'w') as homestead_prov_casscli_file:

        # Write Homestead/cassandra-cli header
        homestead_file.write("#!/bin/bash\n")
        homestead_file.write("# Homestead bulk provisioning script for users in %s\n" % (csv_filename))
        homestead_file.write("# Run this script on any node in your Homestead deployment to create the users\n")
        homestead_file.write("# The %s and %s files must also be present on this system\n" % (homestead_cache_casscli_filename, homestead_prov_casscli_filename))
        homestead_file.write("\n")
        homestead_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (homestead_cache_casscli_filename, homestead_cache_casscli_filename))
        homestead_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (homestead_prov_casscli_filename, homestead_prov_casscli_filename))
        homestead_file.write("cassandra-cli -B -f %s\n" % (homestead_cache_casscli_filename))
        homestead_file.write("cassandra-cli -B -f %s\n" % (homestead_prov_casscli_filename))
        homestead_cache_casscli_file.write("USE homestead_cache;\n")
        homestead_prov_casscli_file.write("USE homestead_provisioning;\n")

        for public_id, private_id, realm, password in csv_iterator(csv_filename):

            # Generate the user-specific data
            hash = utils.md5("%s:%s:%s" % (private_id, realm, password))

            public_identity_xml = "<PublicIdentity><BarringIndication>1</BarringIndication><Identity>%s</Identity></PublicIdentity>" % public_id
            initial_filter_xml = ifcs.generate_ifcs(utils.sip_uri_to_domain(public_id))
            ims_subscription_xml = create_imssubscription_xml(private_id, public_identity_xml, initial_filter_xml)
            irs_uuid = str(uuid.uuid4())
            sp_uuid = str(uuid.uuid4())

            # Add the user to the optimized cassandra cache.
            homestead_cache_casscli_file.write(
                create_row_command("impi", private_id))
            homestead_cache_casscli_file.write(
                "SET impi['%s']['digest_ha1'] = '%s';\n" % (private_id, hash))
            homestead_cache_casscli_file.write(
                "SET impi['%s']['digest_realm'] = '%s';\n" % (private_id, realm))
            homestead_cache_casscli_file.write(
                "SET impi['%s']['public_id_%s'] = '';\n" % (private_id,
                                                            public_id))

            homestead_cache_casscli_file.write(
                create_row_command("impu", public_id))
            homestead_cache_casscli_file.write(
                "SET impu['%s']['ims_subscription_xml'] = '%s';\n" % (
                    public_id,
                    ims_subscription_xml.replace("'", "\\'")))

            # Populate the provisioning tables for the user.
            homestead_prov_casscli_file.write(
                create_row_command("implicit_registration_sets", irs_uuid))
            homestead_prov_casscli_file.write(
                "SET implicit_registration_sets['%s']['service_profile_%s'] = lexicaluuid('%s');\n" % (irs_uuid,
                                                                                                       sp_uuid,
                                                                                                       sp_uuid))
            homestead_prov_casscli_file.write(
                "SET implicit_registration_sets['%s']['associated_private_%s'] = utf8('%s');\n" % (irs_uuid,
                                                                                                   private_id,
                                                                                                   private_id))

            homestead_prov_casscli_file.write(
                create_row_command("service_profiles", sp_uuid))
            homestead_prov_casscli_file.write(
                "SET service_profiles['%s']['irs'] = '%s';\n" % (sp_uuid,
                                                                 irs_uuid))
            homestead_prov_casscli_file.write(
                "SET service_profiles['%s']['initialfiltercriteria'] = '%s';\n" % (sp_uuid,
                                                                                   initial_filter_xml))
            homestead_prov_casscli_file.write(
                "SET service_profiles['%s']['public_id_%s'] = utf8('%s');\n" % (sp_uuid,
                                                                                public_id,
                                                                                public_id))

            homestead_prov_casscli_file.write(
                create_row_command("public", public_id))
            homestead_prov_casscli_file.write(
                "SET public['%s']['publicidentity'] = '%s';\n" % (public_id,
                                                                  public_identity_xml))
            homestead_prov_casscli_file.write(
                "SET public['%s']['service_profile'] = '%s';\n" % (public_id,
                                                                   sp_uuid))

            password_to_write = password if write_plaintext_password else ""
            homestead_prov_casscli_file.write(
                create_row_command("private", private_id))
            homestead_prov_casscli_file.write(
                "SET private['%s']['digest_ha1'] = '%s';\n" % (private_id,
                                                               hash))
            homestead_prov_casscli_file.write(
                "SET private['%s']['plaintext_password'] = '%s';\n" % (private_id,
                                                                       password_to_write))
            homestead_prov_casscli_file.write(
                "SET private['%s']['realm'] = '%s';\n" % (private_id, realm))
            homestead_prov_casscli_file.write(
                "SET private['%s']['associated_irs_%s'] = lexicaluuid('%s');\n" % (private_id,
                                                                                   irs_uuid,
                                                                                   irs_uuid))

    # Make the created .sh files executable
    permissions = stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE
    os.chmod(homestead_filename, permissions)

    print "Generated homestead bulk provisioning scripts"
    print "- %-46s - run this script on Homestead" % (homestead_filename)
    print "- %-46s - copy this file onto Homestead" % (homestead_cache_casscli_filename)
    print "- %-46s - copy this file onto Homestead" % (homestead_prov_casscli_filename)


def write_homer_scripts(csv_filename):
    csv_filename_prefix = string.replace(csv_filename, ".csv", "")
    xdm_filename = "%s.create_xdm.sh" % (csv_filename_prefix)
    xdm_cqlsh_filename = "%s.create_xdm.cqlsh" % (csv_filename_prefix)

    with open(xdm_filename, 'w') as xdm_file, \
         open(xdm_cqlsh_filename, 'w') as xdm_cqlsh_file:

        # Write Homer/CQL header
        xdm_file.write("#!/bin/bash\n")
        xdm_file.write("# Homer bulk provisioning script for users in %s\n" % (csv_filename))
        xdm_file.write("# Run this script on any node in your Homer deployment to create the users\n")
        xdm_file.write("# The %s file must also be present on this system\n" % (xdm_cqlsh_filename))
        xdm_file.write("\n")
        xdm_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (xdm_cqlsh_filename, xdm_cqlsh_filename))
        xdm_file.write("cqlsh -f %s\n" % (xdm_cqlsh_filename))
        xdm_cqlsh_file.write("USE homer;\n")

        for public_id, private_id, realm, password in csv_iterator(csv_filename):
            # Add the simservs document for the user to the documents table on Homer
            xdm_cqlsh_file.write(
                "INSERT INTO simservs (user, value) VALUES ('%s', '%s');\n" % (public_id,
                                                                               SIMSERVS))

    # Make the created .sh files executable
    permissions = stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE
    os.chmod(xdm_filename, permissions)

    print "Generated homer bulk provisioning scripts"
    print "- %-46s - run this script on Homer" % (xdm_filename)
    print "- %-46s - copy this file onto Homer" % (xdm_cqlsh_filename)


def write_memento_scripts(csv_filename):
    curr_time = time.time()

    csv_filename_prefix = string.replace(csv_filename, ".csv", "")
    memento_filename = "%s.create_memento.sh" % (csv_filename_prefix)
    memento_casscli_filename = "%s.create_memento.casscli" % (csv_filename_prefix)

    with open(memento_filename, 'w') as memento_file, \
         open(memento_casscli_filename, 'w') as memento_casscli_file:

        # Write Memento/cassandra-cli header
        memento_file.write("#!/bin/bash\n")
        memento_file.write("# Memento bulk provisioning script for users in %s\n" % (csv_filename))
        memento_file.write("# Run this script on any node in your Memento deployment to create dummy call list entries\n")
        memento_file.write("# The %s file must also be present on this system\n" % (memento_casscli_filename))
        memento_file.write("\n")
        memento_file.write("[ -f %s ] || echo \"The %s file must be present on this system.\"\n" % (memento_casscli_filename, memento_casscli_filename))
        memento_file.write("cassandra-cli -B -f %s\n" % (memento_casscli_filename))
        memento_casscli_file.write("USE memento;\n")

        for public_id, private_id, realm, password in csv_iterator(csv_filename):
            # Add the call list entries for this user.
            for ii in range(CALL_LIST_NUM_CALLS):
                t = curr_time - CALL_LIST_TIME_RANGE_S * (1 - (1.0 * ii / CALL_LIST_NUM_CALLS))
                column_prefix = ("call_" +
                                 time.strftime("%Y%m%d%H%M%S", time.gmtime(t)) +
                                 "_" +
                                 "%0.16x" % ii +
                                 "_")

                answered = (random.random() < 0.8)
                outgoing = (random.random() < 0.5)

                if answered:
                    begin_fragment, end_fragment = create_answered_call_list_entries(public_id, outgoing, t)
                    memento_casscli_file.write(
                        "SET call_lists['%s']['%s'] = utf8('%s');\n" % (public_id,
                                                                        column_prefix + "begin",
                                                                        begin_fragment))
                    memento_casscli_file.write(
                        "SET call_lists['%s']['%s'] = utf8('%s');\n" % (public_id,
                                                                        column_prefix + "end",
                                                                        end_fragment))
                else:
                    rejected_fragment = create_rejected_call_list_entry(public_id, outgoing, t)
                    memento_casscli_file.write(
                        "SET call_lists['%s']['%s'] = utf8('%s');\n" % (public_id,
                                                                        column_prefix + "rejected",
                                                                        rejected_fragment))

    # Make the created .sh files executable
    permissions = stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE
    os.chmod(memento_filename, permissions)

    print "Generated memento bulk provisioning scripts"
    print "- %-46s - run this script on Memento" % (memento_filename)
    print "- %-46s - copy this file onto Memento" % (memento_casscli_filename)


def parse_args():

    USAGE_HEADER = """\
Metaswitch Clearwater bulk-provisioning script creation tool

This script must be run on a Homestead node.

This script generates output scripts and configuration files that provision the
Homestead, Homer (XDM), and (optionally) Memento deployments.
"""

    USAGE_FOOTER = """\
Each row in the input CSV file describes a user, and must contain 4 columns:
- public SIP ID
- private SIP ID
- realm
- password

If you have a CSV file with fewer columns, you can autocomplete the remaining
columns using the bulk_autocomplete.py script.
"""

    parser = argparse.ArgumentParser(description = USAGE_HEADER,
                                     epilog = USAGE_FOOTER,
                                     formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument("csv_filename", help="Generate example memento call list entries")
    parser.add_argument("--memento", action="store_true", help="Generate example memento call list entries")
    parser.add_argument("--plaintext_password", action="store_true", help="Store plaintext passwords for the subscriber")
    return parser.parse_args()

def standalone():
    args = parse_args()
    csv_filename = args.csv_filename

    print "Generating bulk provisioning scripts for users in %s..." % (csv_filename)

    try:
        write_homestead_scripts(csv_filename, args.plaintext_password)
        write_homer_scripts(csv_filename)

        if args.memento:
            write_memento_scripts(csv_filename)

    except IOError as e:
        print "Failed to read/write to %s:" % (e.filename)
        traceback.print_exc()

if __name__ == '__main__':
    standalone()
