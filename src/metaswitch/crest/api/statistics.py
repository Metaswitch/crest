# @file statistic.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import logging
import abc
import base
from monotonic import monotonic

# Collect stats every 5 seconds
STATS_PERIOD = 5
_log = logging.getLogger("crest.api")

class Collector(object):
    """
    Abstract base class for all statistics collectors that can be
    used in homestead or homer.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, stat_name):
        self.stat_name = stat_name
        self.start_time = monotonic()

    @abc.abstractmethod
    def refresh(self):
        """
        Publish the stat to the ipc files, if enough time has passed
        since the stat was last published.
        """
        pass

    @abc.abstractmethod
    def reset(self):
        """
        Reset the collected stats after they have been published.
        """
        pass

    def set_process_id(self, process_id):
        self.stat_name += "_" + str(process_id)

class Counter(Collector):
    """
    Counters track how many times a particular event happens over a period
    """

    def __init__(self, stat_name):
        super(Counter, self).__init__(stat_name)
        self.current = 0

    def increment(self):
        self.current += 1
        self.refresh()

    def refresh(self):
        time_difference = monotonic() - self.start_time

        if time_difference > STATS_PERIOD:
            base.zmq.report([self.current], self.stat_name)
            self.reset()

    def reset(self):
        self.current = 0
        self.start_time = monotonic()

class Accumulator(Collector):
    """
    Accumulators track how many times a particular event happens over a period,
    as well as the mean, variance, hwm and lwm values for the stat.
    """

    def __init__(self, stat_name):
        super(Accumulator, self).__init__(stat_name)
        self.current = 0
        self.sigma = 0
        self.sigma_squared = 0
        self.lwm = 0
        self.hwm = 0

    def accumulate(self, latency):
        self.current += 1
        self.sigma += latency
        self.sigma_squared += (latency * latency)

        if (self.lwm > latency or self.lwm == 0):
            self.lwm = latency

        if (self.hwm < latency):
            self.hwm = latency

        self.refresh()

    def refresh(self):
        time_difference = monotonic() - self.start_time
        mean = 0
        variance = 0

        if time_difference > STATS_PERIOD:
            n = self.current * STATS_PERIOD / time_difference

            if self.current > 0:
                mean = self.sigma / self.current
                variance = (self.sigma_squared / self.current) - (mean * mean)

            base.zmq.report([n, mean, variance, self.lwm, self.hwm], self.stat_name)
            self.reset()

    def reset(self):
        self.current = 0
        self.sigma = 0
        self.sigma_squared = 0
        self.lwm = 0
        self.hwm = 0
        self.start_time = monotonic()
