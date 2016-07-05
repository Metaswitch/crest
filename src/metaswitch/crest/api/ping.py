# @file ping.py
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

from cyclone.web import RequestHandler
from telephus.client import CassandraClient
from twisted.internet import defer
from .passthrough import PassthroughHandler


class PingHandler(RequestHandler):
    @defer.inlineCallbacks
    def get(self):
        # We've seen cases where the telephus fails to connect to Cassandra,
        # and requests sit on the queue forever without being processed.
        # Catch this error case by making a request here on each Cassandra
        # connection.
        factories = PassthroughHandler.cass_factories.values()
        clients = (CassandraClient(factory) for factory in factories)
        gets = (client.get(key='ping', column_family='ping')
                for client in clients)

        try:
            # Use a DeferredList rather than gatherResults to wait
            # for all of the clients to fail or succeed.
            yield defer.DeferredList(gets, consume_errors=True)
        except Exception:
            # We don't care about the result, just whether it returns
            # in a timely fashion. Writing a log would be spammy.
            pass

        self.finish("OK")
