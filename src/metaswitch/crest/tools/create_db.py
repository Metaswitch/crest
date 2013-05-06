#!/usr/bin/env python

# @file create_db.py
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


import logging

from metaswitch.crest import logging_config
from metaswitch.crest.tools import connection
from metaswitch.crest.api import get_create_statements

_log = logging.getLogger("crest.create_db")

def standalone():
    c = connection.cursor()
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
    c.close()

if __name__ == '__main__':
    logging_config.configure_logging("create_db")
    standalone()
