# @file __init__.py
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

import collections

from metaswitch.crest.api import _base
from metaswitch.crest.api.ping import PingHandler
from metaswitch.crest import settings


def load_module(name):
    """Dynamically load routes and database CREATE statements from configured
    modules"""
    return __import__("metaswitch.crest.api.%s" % name,
                      fromlist=["ROUTES", "CREATE_STATEMENTS"])


def get_routes():
    """Get all the routes for the webserver.  This includes the default routes,
    plus the routes for all the installed submodules"""
    return sum([load_module(m).ROUTES for m in settings.INSTALLED_HANDLERS], []) + ROUTES


def get_create_statements():
    """
    Get all the statements for creating the necessary database tables.

    Each application must define a CREATE_STATEMENTS module attribute that is a
    dictionary mapping keyspaces to a list of statements creating tables in that
    keyspace.  This function merges these into one dictionary.
    """
    statement_dict = collections.defaultdict(list)

    for m in settings.INSTALLED_HANDLERS:
        for keyspace, statements in load_module(m).CREATE_STATEMENTS.items():
            statement_dict[keyspace] += statements

    return statement_dict


def initialize(application):
    for m in [load_module(m) for m in settings.INSTALLED_HANDLERS]:
        try:
            m.initialize(application)
        except AttributeError:
            # No initializer for module
            pass


PATH_PREFIX = "^/"

# Basic routes for application. See modules (e.g. api.homestead.__init__) for actual application routes
ROUTES = [
    # Liveness ping.
    (PATH_PREFIX + r'ping/?$', PingHandler),

    # JSON 404 page for API calls.
    (PATH_PREFIX + r'.*$', _base.UnknownApiHandler),
]
