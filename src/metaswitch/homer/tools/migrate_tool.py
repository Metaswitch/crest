#!/usr/bin/env python

# @file migrate_tool.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


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

    args = parser.parse_args()

    standalone()
