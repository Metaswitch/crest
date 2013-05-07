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


import json
import unittest

from metaswitch.crest import settings
from metaswitch.crest.main import create_application

class AppTestCase(unittest.TestCase):
    """
    Base class for FV tests that boot up the whole app (excluding the storage 
    layer).
    """
    def get_app(self):
        return create_application()

    def fetch(self, path, expected_status=200, *args, **kwargs):
        """
        Fetches the given path.
        
        :arg string url: URL to fetch
        :arg string method: HTTP method, e.g. "GET" or "POST"
        :arg headers: Additional HTTP headers to pass on the request
        :type headers: `~cyclone.httputil.HTTPHeaders` or `dict`
        :arg string auth_username: Username for HTTP "Basic" authentication
        :arg string auth_password: Password for HTTP "Basic" authentication
        :arg float connect_timeout: Timeout for initial connection in seconds
        :arg float request_timeout: Timeout for entire request in seconds
        :arg datetime if_modified_since: Timestamp for ``If-Modified-Since``
           header
        :arg bool follow_redirects: Should redirects be followed automatically
           or return the 3xx response?
        :arg int max_redirects: Limit for `follow_redirects`
        :arg string user_agent: String to send as ``User-Agent`` header
        :arg bool use_gzip: Request gzip encoding from the server
        :arg string network_interface: Network interface to use for request
        :arg callable streaming_callback: If set, `streaming_callback` will
           be run with each chunk of data as it is received, and
           `~HTTPResponse.body` and `~HTTPResponse.buffer` will be empty in
           the final response.
        :arg callable header_callback: If set, `header_callback` will
           be run with each header line as it is received, and
           `~HTTPResponse.headers` will be empty in the final response.
        :arg callable prepare_curl_callback: If set, will be called with
           a `pycurl.Curl` object to allow the application to make additional
           `setopt` calls.
        :arg string proxy_host: HTTP proxy hostname.  To use proxies,
           `proxy_host` and `proxy_port` must be set; `proxy_username` and
           `proxy_pass` are optional.  Proxies are currently only support
           with `curl_httpclient`.
        :arg int proxy_port: HTTP proxy port
        :arg string proxy_username: HTTP proxy username
        :arg string proxy_password: HTTP proxy password
        :arg bool allow_nonstandard_methods: Allow unknown values for `method`
           argument?
        :arg bool validate_cert: For HTTPS requests, validate the server's
           certificate?
        :arg string ca_certs: filename of CA certificates in PEM format,
           or None to use defaults.  Note that in `curl_httpclient`, if
           any request uses a custom `ca_certs` file, they all must (they
           don't have to all use the same `ca_certs`, but it's not possible
           to mix requests with ca_certs and requests that use the defaults.
        :arg bool allow_ipv6: Use IPv6 when available?  Default is false in
           `simple_httpclient` and true in `curl_httpclient`
        :arg string client_key: Filename for client SSL key, if any
        :arg string client_cert: Filename for client SSL certificate, if any
        """
        if "body" in kwargs:
            body = kwargs["body"]
            if isinstance(body, dict):
                kwargs["body"] = json.dumps(body)
        resp = super(AppTestCase, self).fetch(path, *args, **kwargs)

        self.assertEqual(resp.code, expected_status)
        return resp

    def assert_json_response(self, resp, expected):
        self.assertEquals(resp.code, 200)
        j = json.loads(resp.body)
        self.assertEquals(j, expected)

    def get_json_from_response(self, resp, expected_code=200):
        self.assertEqual(resp.code, expected_code)
        return json.loads(resp.body)

