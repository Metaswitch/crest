# @file ping.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import logging
from cyclone.web import RequestHandler
from telephus.client import CassandraClient
from twisted.internet import defer

_log = logging.getLogger("crest.ping")

# This class responds to pings - we use it to confirm that Homer/Homestead-prov
# are still responsive and functional
class PingHandler(RequestHandler):
    cass_factories = []

    @classmethod
    def register_cass_factory(cls, factory):
        cls.cass_factories.append(factory)

    @defer.inlineCallbacks
    def get(self):
        # Attempt to connect to Cassandra (by asking for a non-existent key).
        # We need this check as we've seen cases where telephus fails to
        # connect to Cassandra, and requests sit on the queue forever without
        # being processed.
        clients = (CassandraClient(factory) for factory in self.cass_factories)

        # If Cassandra is up, it will throw an exception (because we're asking
        # for a nonexistent key). That's fine - it proves Cassandra is up and
        # we have a connection to it. If Cassandra is down, this call will
        # never return and Monit will time it out and kill the process for
        # unresponsiveness.

        # Catch the Twisted error made (as 'ping' isn't a configured column) -
        # as with the Exception we don't care about the error, we just want to
        # test if we can contact Cassandra
        def ping_error(err): # pragma: no cover
            pass

        try:
            _log.debug("Handling ping request")
            gets = (client.get(key='ping', column_family='ping').addErrback(ping_error)
                    for client in clients)
            yield defer.DeferredList(gets)
        except Exception:
            # We don't care about the result, just whether it returns
            # in a timely fashion. Writing a log would be spammy.
            pass

        _log.debug("Handled ping request successfully")

        self.finish("OK")
