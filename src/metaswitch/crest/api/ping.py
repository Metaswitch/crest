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


# This class responds to pings - we use it to confirm that Homer/Homestead-prov
# are still responsive and functional
class PingHandler(RequestHandler):
    @defer.inlineCallbacks
    def get(self):
        # Attempt to connect to Cassandra (by asking for a non-existent key).
        # We need this check as we've seen cases where telephus fails to
        # connect to Cassandra, and requests sit on the queue forever without
        # being processed.
        factories = PassthroughHandler.cass_factories.values()
        clients = (CassandraClient(factory) for factory in factories)
        gets = (client.get(key='ping', column_family='ping')
                for client in clients)

        # If Cassandra is up, it will throw an expection (because we're asking
        # for a nonexistent key). That's fine - it proves Cassandra is up and
        # we have a connection to it. If Cassandra is down, this call will
        # never return and Monit will time it out and kill the process for
        # unresponsiveness.
        try:
            yield defer.DeferredList(gets)
        except Exception:
            # We don't care about the result, just whether it returns
            # in a timely fashion. Writing a log would be spammy.
            pass

        self.finish("OK")
