# @file lastvaluecache.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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
    def __init__(self, process_name):
        # Set up the cache.
        self.cache = {}
        self.zmq_address = "ipc:///var/run/clearwater/stats/" + process_name

    def bind(self, p_id, worker_proc):
        self.context = zmq.Context()

        # Connect to the ipc file where all stats are published.
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect("ipc:///tmp/stats0")

        # If this is the parent process, then subscribe to the ipc file.
        if p_id == 0:
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.bind("ipc:///tmp/stats0")
            for process_id in range (0, worker_proc):
                for stat in VALID_STATS:
                    self.subscriber.setsockopt(zmq.SUBSCRIBE,
                                               stat + "_" + str(process_id))

            # Set up a tcp connection to publish all stats, including
            # repeat subscriptions. If the bind fails, log this and carry on.
            self.broadcaster = self.context.socket(zmq.XPUB)
            self.broadcaster.setsockopt(zmq.XPUB_VERBOSE, 1)
            try:
                self.broadcaster.bind(self.zmq_address)
            except zmq.error.ZMQError as e:
                _log.debug("The broadcaster bind failed; no statistics will be published: " + str(e))

            # Set up a poller to listen for new stats published to the
            # ipc file and for new external subscriptions
            self.poller = zmq.Poller()
            self.poller.register(self.subscriber, zmq.POLLIN)
            self.poller.register(self.broadcaster, zmq.POLLIN)

            self.forward()

    def unbind(self):
        self.context.destroy()
        self.context = None
        self.publisher = None
        self.subscriber = None
        self.broadcaster = None
        self.poller = None

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
