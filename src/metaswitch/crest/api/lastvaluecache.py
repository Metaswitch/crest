# @file lastvaluecache.py
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
import zmq
from twisted.internet import defer, threads

_log = logging.getLogger("crest.api")
VALID_STATS = [
    "P_latency_us",
    "P_queue_size",
    "P_incoming_requests",
    "P_rejected_overload",
]


class LastValueCache:
    def __init__(self, zmq_port):
        # Set up the cache.
        self.cache = {}
        self.zmq_address = "tcp://*:" + str(zmq_port)

    def bind(self, p_id, worker_proc):
        context = zmq.Context()

        # Connect to the ipc file where all stats are published.
        self.publisher = context.socket(zmq.PUB)
        self.publisher.connect("ipc:///tmp/stats0")

        # If this is the parent process, then subscribe to the ipc file.
        if p_id == 0:
            self.subscriber = context.socket(zmq.SUB)
            self.subscriber.bind("ipc:///tmp/stats0")
            for process_id in range (0, worker_proc):
                for stat in VALID_STATS:
                    self.subscriber.setsockopt(zmq.SUBSCRIBE,
                                               stat + "_" + str(process_id))

            # Set up a tcp connection to publish all stats, including
            # repeat subscriptions. If the bind fails, log this and carry on.
            self.broadcaster = context.socket(zmq.XPUB)
            self.broadcaster.setsockopt(zmq.XPUB_VERBOSE, 1)
            try:
                # Crest uses port 6667 for stats so that there isn't a port
                # clash when homestead-prov is co-located with homestead (which
                # uses 6668).
                self.broadcaster.bind(self.zmq_address)
            except zmq.error.ZMQError as e:
                _log.debug("The broadcaster bind failed; no statistics will be published: " + str(e))

            # Set up a poller to listen for new stats published to the
            # ipc file and for new external subscriptions
            self.poller = zmq.Poller()
            self.poller.register(self.subscriber, zmq.POLLIN)
            self.poller.register(self.broadcaster, zmq.POLLIN)

            self.forward()

    @defer.inlineCallbacks
    def last_cache(self):
        # Poll
        d = threads.deferToThread(self.poller.poll)
        answer = yield d
        defer.returnValue(answer)

    @defer.inlineCallbacks
    def forward(self):
        # Continually poll for updates
        while True:
            # Poll returns a dictionary of sockets
            answer = yield self.last_cache()

            if self.subscriber in dict(answer):
                # A stat has been updated in the ipc file. Update
                # the cache, and publish the new stat. The stat will
                # be of the form [stat_name, "OK", values...]
                msg = yield self.subscriber.recv_multipart()
                self.cache[msg[0]] = msg
                self.broadcaster.send_multipart(msg)
            if self.broadcaster in dict(answer):
                # A new subscription for a stat has occurred. Immediately
                # send the value stored in the cache (if it exists)
                event = yield self.broadcaster.recv()

                # The first element is whether this is a subscripion (1)
                # or to unsubscriber (0)
                if event[0] == b'\x01':
                    topic = event[1:]
                    if topic in self.cache:
                        self.broadcaster.send_multipart(self.cache[topic])
                    else:
                        # No cached value - return empty statistic.
                        self.broadcaster.send_multipart([topic, "OK"])

    def report(self, new_value, stat_name):
        # Publish the updated stat to the ipc file
        self.publisher.send(stat_name, zmq.SNDMORE)
        self.publisher.send("OK", zmq.SNDMORE)

        for index in range(len(new_value) - 1):
            self.publisher.send(str(new_value[index]), zmq.SNDMORE)
        self.publisher.send(str(new_value[-1]))
