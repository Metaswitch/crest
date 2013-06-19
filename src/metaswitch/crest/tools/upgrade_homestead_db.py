#!/usr/bin/env python

# @file upgrade_homestead_db.py
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


import logging
import cql

from metaswitch.crest import logging_config
from metaswitch.crest.tools import connection
from metaswitch.crest.api import get_create_statements
from metaswitch.crest.api.homestead import config

_log = logging.getLogger("crest.upgrade_homestead_db")

def standalone():
    c = connection.cursor()

    try:
        c.execute("select * from public_ids;")
    except cql.ProgrammingError:
        print ("Newer Homestead tables don't exist, create and populate them")
        create_statements = get_create_statements()
        print "Create statements: ", create_statements
        for cs in create_statements:
            try:
                print "executing %s" % cs
                c.execute(cs)
            except Exception:
                _log.exception("Failed to create table")
                pass
            print "Done."

        # For each entry in the SIP_DIGESTS table, create entries in the
        # public_ids and private_ids tables that contain the mapping
        # private_id:<xxx> - public_id:<sip:xxx> - this is what earlier versions
        # of Clearwater simulated but did not store in the database.
        c.execute("SELECT private_id from %s;" % config.SIP_DIGESTS_TABLE)
        private_ids = []
        while True:
            row = c.fetchone()
            if row == None:
                break
            private_ids.append(row[0])
        print ("List of private IDs: %s" % private_ids)

        for priv in private_ids:
            pub = "sip:" + priv
            print ("Inserting private/public ID pair: %s/%s" % (priv, pub))
            try:
                c.execute("INSERT INTO %s (public_id, '%s') values ('%s', '%s');" % (config.PRIVATE_IDS_TABLE, priv, pub, priv))
                c.execute("INSERT INTO %s (private_id, '%s') values ('%s', '%s');" % (config.PUBLIC_IDS_TABLE, pub, priv, pub))
            except Exception:
                _log.exception("Failed to insert private/public ID pair: %s/%s" % (priv, pub))
                pass
            print "Done."

    c.close()

if __name__ == '__main__':
    logging_config.configure_logging("upgrade_homestead_db")
    standalone()
