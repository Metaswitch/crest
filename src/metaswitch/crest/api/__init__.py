# @file __init__.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

from metaswitch.crest.api import base
from metaswitch.crest.api.ping import PingHandler
from metaswitch.crest import settings

# Monkey patch connectionLost method in ThriftClientProtocol - it's a bad
# idea to assume the client request lists is immutable when making error
# callbacks.
from twisted.internet.protocol import connectionDone
from thrift.transport import TTransport
from thrift.transport.TTwisted import ThriftClientProtocol

def connectionLost(self, reason=connectionDone):
    while (self.client._reqs != {}):
        tmp = self.client._reqs
        self.client._reqs = {}
        for k, v in tmp.iteritems():
            tex = TTransport.TTransportException(
                type=TTransport.TTransportException.END_OF_FILE,
                message='Connection closed')
            v.errback(tex)

ThriftClientProtocol.connectionLost = connectionLost


def load_module(name):
    """Dynamically load routes from configured modules"""
    return __import__("metaswitch.%s" % name,
                      fromlist=["ROUTES"])


def get_routes():
    """Get all the routes for the webserver.  This includes the default routes,
    plus the routes for all the installed submodules"""
    return sum([load_module(m).ROUTES for m in settings.INSTALLED_HANDLERS], []) + ROUTES

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
    (PATH_PREFIX + r'.*$', base.UnknownApiHandler),
]
