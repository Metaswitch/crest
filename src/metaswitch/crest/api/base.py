# @file base.py
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
import json
import traceback
import httplib

import msgpack
import cyclone.web
from cyclone.web import HTTPError
from twisted.python.failure import Failure

from telephus.cassandra.ttypes import TimedOutException as CassandraTimeout
from metaswitch.common import utils
from metaswitch.crest import settings
from metaswitch.crest.api.statistics import Accumulator, Counter
from monotonic import monotonic
from metaswitch.crest.api.DeferTimeout import TimeoutError
from metaswitch.crest.api.exceptions import HSSOverloaded, HSSConnectionLost, HSSStillConnecting, UserNotIdentifiable, UserNotAuthorized
from metaswitch.crest.api.lastvaluecache import LastValueCache
from metaswitch.crest import pdlogs

_log = logging.getLogger("crest.api")

class PenaltyCounter:
    def __init__(self):
        # Set up counters for HSS and cache overload responses. Only HSS overload responses
        # are currently tracked.
        self.cache_penalty_count = 0
        self.hss_penalty_count = 0

    def reset_cache_penalty_count(self):
        self.cache_penalty_count = 0

    def reset_hss_penalty_count(self):
        self.hss_penalty_count = 0

    def incr_cache_penalty_count(self):
        self.cache_penalty_count += 1

    def incr_hss_penalty_count(self):
        self.hss_penalty_count += 1

    def get_cache_penalty_count(self):
        _log.debug("%d cache overload penalties hit in current latency tracking period", self.cache_penalty_count)
        return self.cache_penalty_count

    def get_hss_penalty_count(self):
        _log.debug("%d HSS overload penalties hit in current latency tracking period", self.hss_penalty_count)
        return self.hss_penalty_count


class LeakyBucket:
    def __init__(self, max_size, rate):
        self.max_size = max_size
        self.tokens = max_size
        self.rate = rate
        self.replenish_time = monotonic()

    def get_token(self):
        self.replenish_bucket()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        else:
            return False

    def update_rate(self, new_rate):
        self.rate = new_rate

    def update_max_size(self, new_max_size):
        self.max_size = new_max_size

    def replenish_bucket(self):
        replenish_time = monotonic()
        self.tokens += self.rate * (replenish_time - self.replenish_time)
        self.replenish_time = replenish_time
        if self.tokens > self.max_size:
            self.tokens = self.max_size


class LoadMonitor:
    # Number of request processed between each adjustment of the leaky bucket rate
    ADJUST_PERIOD = 20

    # Adjustment parameters for
    DECREASE_THRESHOLD = 0.0
    DECREASE_FACTOR = 1.2
    INCREASE_THRESHOLD = -0.005
    INCREASE_FACTOR = 0.5

    # How many deviations above the average latency is the max latency
    NUM_DEV = 4

    def __init__(self, target_latency, max_bucket_size, init_token_rate, min_token_rate):
        self.accepted = 0
        self.rejected = 0
        self.pending_count = 0
        self.max_pending_count = 0
        self.target_latency = target_latency
        self.smoothed_latency = 0
        self.smoothed_variability = target_latency
        self.max_latency = self.smoothed_latency + (self.NUM_DEV * self.smoothed_variability)
        self.bucket = LeakyBucket(max_bucket_size, init_token_rate)
        self.adjust_count = self.ADJUST_PERIOD
        self.min_token_rate = min_token_rate
        self.overloaded = False

    def admit_request(self):
        if self.bucket.get_token():
            # Got a token from the bucket, so admit the request
            if self.overloaded:
                pdlogs.API_NOTOVERLOADED.log()
                self.overloaded = False
            self.accepted += 1
            self.pending_count += 1
            queue_size_accumulator.accumulate(self.pending_count)
            if self.pending_count > self.max_pending_count:
                self.max_pending_count = self.pending_count
            return True
        else:
            if not self.overloaded:
                pdlogs.API_OVERLOADED.log()
                self.overloaded = True
            self.rejected += 1
            return False

    def request_complete(self):
        self.pending_count -= 1

    def update_latency(self, latency):
        self.smoothed_latency = (7 * self.smoothed_latency + latency) / 8
        self.smoothed_variability = (7 * self.smoothed_variability + abs(latency - self.smoothed_latency)) / 8
        self.max_latency = self.smoothed_latency + (self.NUM_DEV * self.smoothed_variability)
        self.adjust_count -= 1

        if self.adjust_count <= 0:
            # This algorithm is based on the Welsh and Culler "Adaptive Overload
            # Control for Busy Internet Servers" paper, although based on a smoothed
            # mean latency, rather than the 90th percentile as per the paper.
            # Also, the additive increase is scaled as a proportion of the maximum
            # bucket size, rather than an absolute number as per the paper.
            accepted_percent = 100
            if (self.accepted + self.rejected) != 0:
                accepted_percent = 100 * (float(self.accepted) / float(self.accepted + self.rejected))

            self.accepted = 0
            self.rejected = 0
            self.adjust_count = self.ADJUST_PERIOD
            err = (self.smoothed_latency - self.target_latency) / self.target_latency
            hss_overloads = penaltycounter.get_hss_penalty_count()
            if ((err > self.DECREASE_THRESHOLD) or (hss_overloads > 0)):
                # latency is above where we want it to be, or we are getting overload responses from the HSS,
                # so adjust the rate downwards by a multiplicative factor
                new_rate = self.bucket.rate / self.DECREASE_FACTOR
                if new_rate < self.min_token_rate:
                    new_rate = self.min_token_rate
                _log.info("Accepted %f requests, latency error = %f, HSS overloads = %d, decrease rate %f to %f" %
                                 (accepted_percent, err, hss_overloads, self.bucket.rate, new_rate))
                self.bucket.update_rate(new_rate)
            elif err < self.INCREASE_THRESHOLD:
                # latency is sufficiently below the target, so we can increase by an additive
                # factor - weighted by how far below target we are.
                new_rate = self.bucket.rate + (-err) * self.bucket.max_size * self.INCREASE_FACTOR
                _log.info("Accepted %f%% of requests, latency error = %f, increase rate %f to %f" %
                                (accepted_percent, err, self.bucket.rate, new_rate))
                self.bucket.update_rate(new_rate)
            else:
                _log.info("Accepted %f%% of requests, latency error = %f, rate %f unchanged" %
                                (accepted_percent, err, self.bucket.rate))

        penaltycounter.reset_hss_penalty_count()

# Create load monitor with target latency of 100ms, maximum bucket size of
# 20 requests, initial and minimum token rate of 10 per second
loadmonitor = LoadMonitor(0.1, 20, 10, 10)
penaltycounter = PenaltyCounter()

# Create the accumulators and counters
zmq = LastValueCache(settings.PROCESS_NAME)
latency_accumulator = Accumulator("P_latency_us")
queue_size_accumulator = Accumulator("P_queue_size")
incoming_requests = Counter("P_incoming_requests")
overload_counter = Counter("P_rejected_overload")

# Update the accumulators and counters when the process id is known,
# and set up the zmq bindings
def setupStats(p_id, worker_proc):
    zmq.bind(p_id, worker_proc)
    latency_accumulator.set_process_id(p_id)
    queue_size_accumulator.set_process_id(p_id)
    incoming_requests.set_process_id(p_id)
    overload_counter.set_process_id(p_id)

def shutdownStats():
    zmq.unbind()

def _guess_mime_type(body):
    if (body == "null" or
        (body[0] == "{" and
         body[-1] == "}") or
        (body[0] == "[" and
         body[-1] == "]")):
        _log.warning("Guessed MIME type of uploaded data as JSON. Client should specify.")
        return "json"
    else:
        _log.warning("Guessed MIME type of uploaded data as URL-encoded. Client should specify.")
        return "application/x-www-form-urlencoded"


class BaseHandler(cyclone.web.RequestHandler):
    """
    Base class for our web handlers, should handle shared concerns like
    authenticating requests and post-processing data.
    """

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.__request_data = None

    def should_count_requests_in_latency(self):
        return True

    def prepare(self):
        # Increment the request counter
        incoming_requests.increment()

        # timestamp the request
        self._start = monotonic()
        _log.info("Received request from %s - %s %s://%s%s" %
                   (self.request.remote_ip, self.request.method, self.request.protocol, self.request.host, self.request.uri))
        if not loadmonitor.admit_request():
            _log.warning("Rejecting request because of overload")
            overload_counter.increment()
            return Failure(HTTPError(httplib.SERVICE_UNAVAILABLE))

    def on_finish(self):
        _log.info("Sending %s response to %s for %s %s://%s%s" %
                   (self.get_status(),
                    self.request.remote_ip,
                    self.request.method,
                    self.request.protocol,
                    self.request.host,
                    self.request.uri))

        loadmonitor.request_complete()
        latency = monotonic() - self._start
        if self.should_count_requests_in_latency():
            loadmonitor.update_latency(latency)

        # Track the latency of the requests (in usec)
        latency_accumulator.accumulate(latency * 1000000)

    def write(self, chunk):
        if (isinstance(chunk, dict) and
             "application/x-msgpack" in self.request.headers.get("Accept", "")):
            _log.debug("Responding with msgpack")
            self.set_header("Content-Type", "application/x-msgpack")
            chunk = msgpack.dumps(chunk)
        _log.debug("Writing response body: %s" % chunk)
        cyclone.web.RequestHandler.write(self, chunk)

    def _query_data(self, args):
        ret = {}
        for k in args:
            if len(args[k]) == 1:
                ret[k] = args[k][0]
            else:
                ret[k] = args[k]
        return ret

    def _handle_request_exception(self, e):
        """
        Overridden to intercept the exception object and pass to send_error
        """
        err_traceback = traceback.format_exc()
        orig_e = e
        if e.__class__ == Failure:
            err_traceback = e.getTraceback()
            e = e.value

        if type(e) == HTTPError:
            if e.log_message:
                format = "%d %s: " + e.log_message
                args = [e.status_code, self._request_summary()] + list(e.args)
                pdlogs.API_HTTPERROR.log(error=format % tuple(args))
                _log.warning(format, *args)
            if e.status_code not in httplib.responses:
                pdlogs.API_HTTPERROR.log(error="bad status code %d for %s" % (e.status_code, self._request_summary()))
                _log.warning("Bad HTTP status code: %d", e.status_code)
                cyclone.web.RequestHandler._handle_request_exception(self, e)
            else:
                _log.debug("Sending HTTP error: %d", e.status_code)
                self.send_error(e.status_code, httplib.responses[e.status_code], exception=e)
        elif type(e) == HSSOverloaded:
                _log.error("Translating HSS overload error into a 502 status code", type(e))
                self.send_error(502)
        elif type(e) in [HSSStillConnecting, HSSConnectionLost, TimeoutError, CassandraTimeout]:
                _log.error("Translating internal %s error into a 503 status code", type(e))
                self.send_error(503)
        elif type(e) == UserNotIdentifiable:
                _log.error("Translating user not identifiable error into a 404 status code", type(e))
                self.send_error(404)
        elif type(e) == UserNotAuthorized:
                _log.error("Translating user not authorized error into a 403 status code", type(e))
                self.send_error(403)
        else:
            pdlogs.API_UNCAUGHT_EXCEPTION.log(exception="%s - %s" % (repr(e), self._request_summary()))
            _log.error("Uncaught exception %s\n%r", self._request_summary(), self.request)
            _log.error("Exception: %s" % repr(e))
            _log.error(err_traceback)
            utils.write_core_file(settings.LOG_FILE_PREFIX, traceback.format_exc())
            cyclone.web.RequestHandler._handle_request_exception(self, orig_e)

    @property
    def request_data(self):
        """The data parsed form the body (JSON and form encoding supported)."""
        if self.__request_data is None:
            self.__request_data = {}
            body = self.request.body
            if body:
                headers = self.request.headers
                type = headers.get("Content-Type", None)
                if type is None:
                    type = _guess_mime_type(body)
                if "json" in type:
                    self.__request_data = json.loads(body)
                else:
                    self.__request_data = self._query_data(self.request.arguments)
        return self.__request_data

    def send_error(self, status_code=500, reason="unknown", detail={}, **kwargs):
        """
        Sends an error response to the client, finishing the request in the
        process.

        If the client has requested an error redirect rather than a status
        code then the error is formatted into URL parameters and sent on the
        redirect instead.
        """
        redirect_url = self.get_argument("onfailure", None)
        if reason == "unknown" and "exception" in kwargs:
            e = kwargs["exception"]
            if isinstance(e, HTTPError):
                reason = e.log_message or "unknown"
        if redirect_url:
            # The client (likely a webpage) has requested that we signal
            # failure by redirecting to a specific URL.
            redirect_url = utils.append_url_params(redirect_url,
                                                   error="true",
                                                   status=status_code,
                                                   message=httplib.responses[status_code],
                                                   reason=reason,
                                                   detail=json.dumps(detail))
            self.redirect(redirect_url)
        else:
            # Handle normally.  this will loop back through write_error below.
            cyclone.web.RequestHandler.send_error(self,
                                                  status_code=status_code,
                                                  reason=reason,
                                                  detail=detail,
                                                  **kwargs)

    def write_error(self, status_code, reason="unknown", detail={}, **kwargs):
        """
        If the status code is not 204 (No Content), write the error page as a
        JSON blob containing information about the error.
        """
        data = None
        if status_code != 204:
            data = {
                "error": True,
                "status": status_code,
                "message": httplib.responses[status_code],
                "reason": reason,
                "detail": detail,
            }
            if self.settings.get("debug") and "exc_info" in kwargs:
                data["exception"] = traceback.format_exception(*kwargs["exc_info"])
        self.finish(data)

    def send_json(self, obj):
        """
        Send and object as a JSON response.

        This is required for types that cyclone does not automatically convert
        to json (such as Lists).
        """
        self.write(json.dumps(obj))
        self.set_header("Content-Type", "application/json")
        self.finish()

    @staticmethod
    def requires_empty_body(func):
        """Decorator that returns a 400 error if an HTTP request does not have
        an empty body"""
        def wrapper(handler, *pos_args, **kwd_args):
            if handler.request.body:
                handler.send_error(400, "Body not empty")
            else:
                return func(handler, *pos_args, **kwd_args)
        return wrapper

    @staticmethod
    def check_request_age(func):
        """Decorator that sends a 503 error (and returns None) if the request
        is too old"""

        # Sprout times out requests that have taken over 500ms
        MAX_REQUEST_TIME = 0.5

        def wrapper(handler, *pos_args, **kwd_args):
            if monotonic() - handler._start > MAX_REQUEST_TIME:
                handler.send_error(503, "Request too old")
            else:
                return func(handler, *pos_args, **kwd_args)
        return wrapper

class UnknownApiHandler(BaseHandler):
    """
    Handler that sends a 404 JSON/msgpack/etc response to all requests.
    """
    def get(self):
        _log.info("Request for unknown API")
        self.send_error(404, "Request for unknown API")

class SlowRequestHandler(BaseHandler):
    """
    Handler that doesn't track the latency of its requests with the load monitor - used for slow requests that won't complete instantly.
    """
    def should_count_requests_in_latency(self):
        return False
