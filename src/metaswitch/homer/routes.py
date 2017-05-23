# @file config.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


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

