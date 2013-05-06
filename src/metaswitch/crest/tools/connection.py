# @file connection.py
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
import threading
from metaswitch.crest import settings
import cql

_log = logging.getLogger("crest.connection")

thread_local = threading.local()

def get():
    return getattr(thread_local, "connection", None)

def get_or_create():
    connection = get()
    if connection == None:
        _log.info("Connecting to Cassandra on %s", settings.CASS_HOST)
        connection = cql.connect(settings.CASS_HOST,
                                 settings.CASS_PORT,
                                 settings.CASS_KEYSPACE,
                                 cql_version='3.0.0')
        assert connection
        thread_local.connection = connection
    return connection

def cursor(*args, **kwargs):
    connection = get_or_create()
    return connection.cursor(*args, **kwargs)

def cycle():
    connection = get()
    if connection != None:
        thread_local.connection = None
        connection.close()

