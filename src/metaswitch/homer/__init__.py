# @file __init__.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


from twisted.internet import reactor
from telephus.protocol import ManagedCassandraClientFactory

from metaswitch.crest.api.passthrough import PassthroughHandler
from metaswitch.crest.api.ping import PingHandler
from metaswitch.crest import settings
from metaswitch.homer import routes

# Routes for application
ROUTES = routes.get_routes()

def initialize(application):
    """Module initialization"""
    factory = ManagedCassandraClientFactory("homer")
    reactor.connectTCP(settings.CASS_HOST,
                       settings.CASS_PORT,
                       factory)
    PassthroughHandler.add_cass_factory("homer", factory)
    PingHandler.register_cass_factory(factory)
