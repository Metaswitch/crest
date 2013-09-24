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

import db
from metaswitch.crest import logging_config

_log = logging.getLogger("crest.upgrade_homestead_db")

def migration_needed():
    """Work out whether we need to migrate the database to the latest schema"""

    # If we can't list rows from a table and keyspace that should exist, the
    # database must need migrating.
    try:
        c = connection.cursor("homestead_cache")
        try:
            c.execute("select * from impi;")
        except:
            return True
        finally:
            c.close()
    except:
        return True

    return False

def standalone():
    if migration_needed():
        print ("Newer Homestead tables don't exist, create and populate them")
        db.create_tables(_log)

    # TODO Migrate data, and/or clean up old tables.

if __name__ == '__main__':
    logging_config.configure_logging("upgrade_homestead_db")
    standalone()
