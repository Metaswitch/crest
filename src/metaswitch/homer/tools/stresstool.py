#!/usr/bin/env python

# @file stresstool.py
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


import argparse
import logging
import time
import random
import os

os.environ.setdefault('CREST_SETTINGS', '/usr/share/clearwater/homer/local_settings.py')

from metaswitch.common.logging_config import configure_logging
from metaswitch.crest import settings
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient

_log = logging.getLogger("crest.stresstool")

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient",
                          max_clients=1000)

max_phone_number = 999
io_loop = None
callback_frequency = 10
get_rate = 1000
server_prefix = None
SIP_DIGEST_REALM = "cw-ngv.com"

def standalone(args):
    global io_loop
    global server_prefix
    global get_rate
    configure_logging(settings.LOG_LEVEL, settings.LOGS_DIR, settings.LOG_FILE_PREFIX, "stresstool")
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("crest").setLevel(logging.DEBUG)
    _log.info("Starting stress against %s", args.server)
    server_prefix = "http://%s" % args.server
    get_rate = args.rate
    io_loop = IOLoop.instance()
    io_loop.add_callback(simulate_xdm_gets)
    io_loop.add_callback(print_histograms)
    io_loop.start()

def simulate_xdm_gets():
    now = time.time()
    for _ in xrange(get_rate / callback_frequency):
        req = Request(get_url(),
                      "digest")
        io_loop.add_callback(req.start_request)
    io_loop.add_timeout(now + 1.0 / callback_frequency,
                        simulate_xdm_gets)

def get_url():
    x = random.randint(0, max_phone_number)
    pid = "sip:%010d@%s" % (6505550000 + x, SIP_DIGEST_REALM)
    url = server_prefix + "/org.etsi.ngn.simservs/users/%s/simservs.xml" % pid
    return url

DEFAULT_FETCH_ARGS = {
    "connect_timeout": 5,
    "request_timeout": 5,
}
"""
    :arg string url: URL to fetch
    :arg string method: HTTP method, e.g. "GET" or "POST"
    :arg headers: Additional HTTP headers to pass on the request
    :type headers: `~tornado.httputil.HTTPHeaders` or `dict`
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

class Histogram():
    def __init__(self, bin_width):
        self.bin_width = bin_width
        self.bins = {}
        self.count = 0

    def accumulate(self, value):
        self.count += 1
        key = int(value / self.bin_width) * self.bin_width
        current = self.bins.setdefault(key, 0)
        self.bins[key] = current + 1

    def __str__(self):
        str = ""
        cum = 0
        for k, v in sorted(self.bins.iteritems()):
            pct = 100.0 * v / self.count
            cum += pct
            str += "%s-%ss\t%s\t%.1f%%\t%.1f%%\n" % (k,
                                                     k + self.bin_width,
                                                     v,
                                                     pct,
                                                     cum)
        return str

start_time = time.time()
all_requests_histogram = Histogram(0.05)
success_histogram = Histogram(0.05)
delay_histogram = Histogram(0.05)
timeout_count = 0

def print_histograms():
    now = time.time()
    run_time = now - start_time
    print "==== Stats ===="
    print "Running for %.1fs" % (run_time,)
    print "Overall rate: %.1f/s" % (all_requests_histogram.count / run_time)
    print "All:", all_requests_histogram.count
    print "Success:", success_histogram.count
    print "Timeout:", timeout_count
    print "Failed:", all_requests_histogram.count - success_histogram.count
    print
    print "==== All requests ===="
    print all_requests_histogram
    print "==== Successful requests ===="
    print success_histogram
    print "==== Delay ===="
    print delay_histogram
    io_loop.add_timeout(time.time() + 2, print_histograms)

def accumulate_request(req):
    all_requests_histogram.accumulate(req.response_time)
    delay_histogram.accumulate(req.delay_time)
    if str(req.response.code)[0] == "2":
        success_histogram.accumulate(req.response_time)
    elif req.response.code == 499:
        global timeout_count
        timeout_count += 1
    else:
        _log.warn("Request failed %s", req.response)

class Request(object):
    def __init__(self, url, tag, method="GET", headers={}, **extra_fetch_args):
        self.creation_time = time.time()
        self.schedule_time = None
        self.completion_time = None
        self.response = None
        self.url = url
        self.method = method
        self.headers = headers
        for k, v in DEFAULT_FETCH_ARGS.iteritems():
            if k not in extra_fetch_args:
                extra_fetch_args[k] = v
        self.extra_fetch_args = extra_fetch_args

    def start_request(self):
        self.schedule_time = time.time()
        client = AsyncHTTPClient()
        client.fetch(self.url,
                     self.on_request_complete,
                     method=self.method,
                     headers=self.headers,
                     **self.extra_fetch_args)

    def on_request_complete(self, response):
        self.completion_time = time.time()
        self.response = response
        accumulate_request(self)

    @property
    def response_time(self):
        return self.completion_time - self.schedule_time

    @property
    def delay_time(self):
        return self.schedule_time - self.creation_time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('server', metavar='SERVER', type=str,
                       help='The domain name or IP address to stress.')
    parser.add_argument('--get-rate', metavar='RATE', type=int,
                       help='The number of requests per second.',
                       dest="rate", default=100)

    args = parser.parse_args()

    standalone(args)
