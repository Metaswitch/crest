#!/usr/bin/env python

# @file migrate_tool.py
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
import urllib

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient

_log = logging.getLogger("crest.migrate_tool")

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient",
                          max_clients=100)

DIGEST_REALM = "cw-ngv.com"
pending_requests = 0
args = None

def handle_get(response):
    global pending_requests
    url = response.request.url
    if not response.error:
        print "Succesfully GET from %s" % url
        http_client = AsyncHTTPClient()
        to_url = url.replace(args.from_server, args.to_server)
        print "Putting to %s " % to_url
        http_client.fetch(to_url, handle_put,
                          method='PUT', body=response.body)
    else:
        pending_requests -= 1
        if pending_requests == 0:
            IOLoop.instance().stop()

def handle_put(response):
    global pending_requests
    url = response.request.url
    if not response.error:
        print "Succesfully PUT to %s" % url
    else:
        print "Error while executing PUT to %s" % url
        print response.error
    pending_requests -= 1
    if pending_requests == 0:
        IOLoop.instance().stop()

def get_user(n, pstn=False):
    if pstn:
        return "sip:+1%010d@%s" % (5108580270 + n, DIGEST_REALM)
    else:
        return "sip:%010d@%s" % (6505550000 + n, DIGEST_REALM)

def get_url(user):
    return "/org.etsi.ngn.simservs/users/%s/simservs.xml" % urllib.quote(user)

def standalone():
    global pending_requests
    pending_requests = args.range
    http_client = AsyncHTTPClient()
    for n in range(args.range):
        user = get_user(n, args.pstn)
        url = get_url(user)
        from_url = args.from_server + url
        print "Fetching from %s " % from_url
        http_client.fetch(from_url, handle_get)
    IOLoop.instance().start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('from_server', metavar='FROM_SERVER', type=str,
                       help='The domain name or IP address to copy from.')
    parser.add_argument('to_server', metavar='TO_SERVER', type=str,
                       help='The domain name or IP address to copy to.')
    parser.add_argument('--number-range', metavar='RANGE', type=int,
                       help='The number range to copy across',
                       dest="range", default=10)
    parser.add_argument('--pstn', action='store_true',
                       help='Use PSTN number range')

    global args
    args = parser.parse_args()

    standalone()
