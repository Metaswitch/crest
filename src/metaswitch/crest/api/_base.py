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

from metaswitch.common import utils
from metaswitch.crest import settings
import sys

_log = logging.getLogger("crest.api")

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
        _log.debug(self.request)

    def write(self, chunk):
        if (isinstance(chunk, dict) and
            "application/x-msgpack" in self.request.headers.get("Accept", "")):
            _log.debug("Responding with msgpack")
            self.set_header("Content-Type", "application/x-msgpack")
            chunk = msgpack.dumps(chunk)
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
                self.send_error(e.status_code, e_info=sys.e_info(), exception=e)
        else:
            logging.error("Uncaught exception %s\n%r", self._request_summary(), self.request)
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


class UnknownApiHandler(BaseHandler):
    """
    Handler that sends a 404 JSON/msgpack/etc response to all requests.
    """
    def get(self):
        self.send_error(404)
