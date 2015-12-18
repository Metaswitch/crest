# @file config.py
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


import json
import logging
import os

from metaswitch.crest.api import PATH_PREFIX

from . import validator

_log = logging.getLogger("crest.api.homer")

HANDLERS_DIR = '/usr/share/clearwater/homer/handlers'
SCHEMA_DIR = '/usr/share/clearwater/homer/schemas'

# TODO More precise regexes
USER = r'[^/]+'

# Routes for application. Each route consists of:
# - The actual route regex, with capture groups for parameters that will be passed to the the Handler
# - The Handler to process the request. If no validation is required, use the PassthroughHandler.
#   To validate requests, subclass PassthroughHandler and validate before passing onto PassthroughHandler
# - Cassandra information. This hash contains the information required by PassthroughHandler to store
#   the data in the underlying database. Namely:
#     - table: the table to store the values in
#     - keys: a list of keys to use for the parameters passed in. These correspond one to one to
#       parameters from the capture groups in the route regex

def load_routes(filename):
    """Loads routes from a JSON description file"""

    routes = []

    with open(filename) as f:
        config = json.load(f)

    for route in config['routes']:
        # Load the route from the JSON description.  The cassandra parameters must be in strings
        # rather than unicode strings.
        routes.append(
            (PATH_PREFIX + route['path'] + '/(' + USER + ')/' + route['file'] + '/?',
            validator.create_handler(os.path.join(SCHEMA_DIR, route['schema'])),
            {'factory_name': 'homer', 'table': str(route['table']), 'column': str(route['column'])}))

    return routes


def get_routes():
    """Get the list of routes for homer"""

    routes = []

    if os.path.isdir(HANDLERS_DIR):
        for filename in os.listdir(HANDLERS_DIR):
            filepath = os.path.join(HANDLERS_DIR, filename)
            if filename.endswith('.json') and os.path.isfile(filepath):
                try:
                    routes.extend(load_routes(filepath))
                except Exception:
                    _log.exception('Failed to load routes from %s', filename)

    return routes

