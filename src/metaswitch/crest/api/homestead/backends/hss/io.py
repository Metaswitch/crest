# @file io.py
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


import logging

from diameter import peer
from twisted.internet import endpoints, reactor
from twisted.internet.protocol import Protocol, Factory

_log = logging.getLogger("crest.api.homestead.hss")


class HSSPeerIOTwisted(Protocol):
    def __init__(self, peer):
        self.peer = peer
        self.in_buffer = r''
        self.in_pos = 0

    def connectionMade(self):
        self.peer._protocol = self
        self.peer.feed(None, 0)
        _log.debug("Connection made")

    def dataReceived(self, data):
        self.in_buffer += data
        self.in_pos += len(data)
        consumed = self.peer.feed(self.in_buffer, self.in_pos)
        #_log.debug("Consumed %d" % consumed)
        if consumed > 0:
            self.in_buffer = self.in_buffer[consumed:]
            self.in_pos -= consumed


class TwistedClientFactory(Factory):
    def __init__(self, client_peer):
        self.client_peer = client_peer

    def buildProtocol(self, addr):
        _log.debug("IO connected!")
        return HSSPeerIOTwisted(self.client_peer)

    def delayedConnect(self, endpoint):
        d = endpoint.connect(self)
        _log.debug("Retrying connection")
        d.addErrback(self.failure, endpoint)

    def failure(self, err, endpoint):
        reactor.callLater(10, self.delayedConnect, endpoint)


class TwistedServerFactory(Factory):
    def __init__(self, base_peer):
        self.server_peer = base_peer
        self.stack = base_peer.stack

    def buildProtocol(self, addr):
        client_peer = self.stack.serverV4Accept(self.server_peer, "1.1.1", 11)
        _log.debug("New client accepted")
        return HSSPeerIOTwisted(client_peer)


class HSSPeerIO(peer.PeerIOCallbacks):
    def __init__(self):
        pass

    def write(self, peer, data, length):
        #twisted protocol is in peer._protocol
        peer._protocol.transport.write(data)

    def connectV4(self, peer, host, port):
        factory = TwistedClientFactory(peer)
        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        _log.debug("Connecting to %s:%d" % (host, port))
        d = endpoint.connect(factory)
        d.addErrback(factory.failure, endpoint)
        pass

    def listenV4(self, peer, host, port):
        factory = TwistedServerFactory(peer)
        endpoint = endpoints.TCP4ServerEndpoint(reactor, port, 50, host)
        _log.debug("Listening on %s:%d" % (host, port))
        endpoint.listen(factory)

    def close(self, peer):
        pass
