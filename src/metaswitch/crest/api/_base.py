# @file _base.py
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

from metaswitch.common import utils
from metaswitch.crest import settings
import sys
import time

_log = logging.getLogger("crest.api")

class LeakyBucket:
    def __init__(self, max_size, rate):
        self.max_size = max_size
        self.tokens = max_size
        self.rate = rate
        self.replenish_time = time.time()

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
        replenish_time = time.time()
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

    def __init__(self, target_latency, max_bucket_size, init_token_rate):
        _log = logging.getLogger("crest.api.loadmonitor")
        _log.debug("Creating load monitor")
        self.accepted = 0
        self.rejected = 0
        self.pending_count = 0
        self.max_pending_count = 0
        self.target_latency = target_latency
        self.smoothed_latency = 0
        self.bucket = LeakyBucket(max_bucket_size, init_token_rate)
        self.adjust_count = self.ADJUST_PERIOD

    def admit_request(self):
        if self.bucket.get_token():
            # Got a token from the bucket, so admit the request
            self.accepted += 1
            self.pending_count += 1
            if self.pending_count > self.max_pending_count:
                self.max_pending_count = self.pending_count
            return True
        else:
            self.rejected += 1
            return False

    def request_complete(self, latency):
        self.pending_count -= 1
        self.smoothed_latency = (7 * self.smoothed_latency + latency) / 8

        self.adjust_count -= 1

        if self.adjust_count <= 0:
            # This algorithm is based on the Welsh and Culler "Adaptive Overload
            # Control for Busy Internet Servers" paper, although based on a smoothed
            # mean latency, rather than the 90th percentile as per the paper.
            # Also, the additive increase is scaled as a proportion of the maximum
            # bucket size, rather than an absolute number as per the paper.
            accepted_percent = 100 * (float(self.accepted) / float(self.accepted + self.rejected))
            self.accepted = 0
            self.rejected = 0
            self.adjust_count = self.ADJUST_PERIOD
            err = (self.smoothed_latency - self.target_latency) / self.target_latency
            if err > self.DECREASE_THRESHOLD:
                # latency is above where we want it to be, so adjust the rate
                # downwards by a multiplicative factor
                new_rate = self.bucket.rate / self.DECREASE_FACTOR
                _log.debug("Accepted %f requests, latency error = %f, decrease rate %f to %f" %
                                 (accepted_percent, err, self.bucket.rate, new_rate))
                self.bucket.update_rate(new_rate)
            elif err < self.INCREASE_THRESHOLD:
                # latency is sufficiently below the target, so we can increase by an additive
                # factor - weighted by how far below target we are.
                new_rate = self.bucket.rate + (-err) * self.bucket.max_size * self.INCREASE_FACTOR
                _log.debug("Accepted %f%% of requests, latency error = %f, increase rate %f to %f" %
                                (accepted_percent, err, self.bucket.rate, new_rate))
                self.bucket.update_rate(new_rate)
            else:
                _log.debug("Accepted %f%% of requests, latency error = %f, rate %f unchanged" %
                                (accepted_percent, err, self.bucket.rate))

# Create load monitor with target latency of 100ms, maximum bucket size of
# 20 requests and initial token rate of 10 per second
_loadmonitor = LoadMonitor(0.1, 20, 10)

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

    def prepare(self):
        # timestamp the request
        self._start = time.time()
        _log.debug("Received request from %s - %s %s://%s%s" %
                   (self.request.remote_ip, self.request.method, self.request.protocol, self.request.host, self.request.uri))
        if not _loadmonitor.admit_request():
            _log.debug("Rejecting request because of overload")
            return Failure(HTTPError(httplib.SERVICE_UNAVAILABLE))

    def on_finish(self):
        latency = time.time() - self._start;
        _loadmonitor.request_complete(latency)

    def write(self, chunk):
        if (isinstance(chunk, dict) and
            "application/x-msgpack" in self.request.headers.get("Accept", "")):
            _log.debug("Responding with msgpack")
            self.set_header("Content-Type", "application/x-msgpack")
            chunk = msgpack.dumps(chunk)
        _log.debug("Sending response to %s - %s %s://%s%s = %s" %
                   (self.request.remote_ip, self.request.method, self.request.protocol, self.request.host, self.request.uri, chunk))
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
        if type(e) == HTTPError:
            if e.log_message:
                format = "%d %s: " + e.log_message
                args = [e.status_code, self._request_summary()] + list(e.args)
                logging.warning(format, *args)
            if e.status_code not in httplib.responses:
                logging.error("Bad HTTP status code: %d", e.status_code)
                cyclone.web.RequestHandler._handle_request_exception(self, e)
            else:
                logging.debug("Sending HTTP error: %d", e.status_code)
                self.send_error(e.status_code, httplib.responses[e.status_code], exception=e)
        else:
            logging.error("Uncaught exception %s\n%r", self._request_summary(), self.request)
            logging.error("Exception: %s" % repr(e))
            logging.error(e.getTraceback())
            cyclone.web.RequestHandler._handle_request_exception(self, e)

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
        Writes the error page as a JSON blob containing information about the
        error.
        """
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

    def send_json(obj):
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
            if not handler.request.body:
                handler.send_error(400, "Body not empty")
            else:
                return func(handler, *pos_args, **kwd_args)
        return wrapper

class UnknownApiHandler(BaseHandler):
    """
    Handler that sends a 404 JSON/msgpack/etc response to all requests.
    """
    def get(self):
        self.send_error(404)
