# @file statistic.py
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

import time
import logging 
import abc
import base
import monotime
from monotime import monotonic_time

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
        self.start_time = monotonic_time()

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
        time_difference = monotonic_time() - self.start_time

        if time_difference > STATS_PERIOD:
            base.zmq.report([self.current], self.stat_name)
            self.reset()

    def reset(self):
        self.current = 0
        self.start_time = monotonic_time()
 
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
        time_difference = monotonic_time() - self.start_time
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
        self.start_time = monotonic_time()
