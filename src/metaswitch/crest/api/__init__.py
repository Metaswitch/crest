# @file __init__.py
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


from cyclone.web import RequestHandler
import cyclone.web

from metaswitch.crest.api import _base
from metaswitch.crest.api.ping import PingHandler
from metaswitch.crest import settings

# Dynamically load routes (and assoicated CREATE statements) from configured modules
def load_module(name):
    return __import__("metaswitch.crest.api.%s" % name,
                      fromlist=["ROUTES", "CREATE_STATEMENTS"])

def get_routes():
    return sum([load_module(m).ROUTES for m in settings.INSTALLED_HANDLERS], []) + ROUTES

def get_create_statements():
    return sum([load_module(m).CREATE_STATEMENTS for m in settings.INSTALLED_HANDLERS], [])

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
