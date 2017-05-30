#! /usr/bin/python

# Copyright (C) Metaswitch Networks 2014
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

"""Restores the gzipped CSV files given on the command line (created with dump-cassandra-to-csv.py) into the Cassandra database. Invoked with './restore-cassandra-from-csv.py file1.csv.gz file2.csv.gz ...' """

from twisted.internet import defer, reactor
from telephus.protocol import ManagedCassandraClientFactory
from telephus.client import CassandraClient
import gzip
import csv
import sys
import uuid
import re

def looks_like_uuid(string):
    re.match('[0-9a-h]{8}-[0-9a-h]{4}-[0-9a-h]{4}-[0-9a-h]{4}-[0-9a-h]{12}', string)

def uuidify(string):
    if looks_like_uuid(string):
        return uuid.UUID(string).bytes
    else:
        return string

@defer.inlineCallbacks
def do_this():
    for gzfilename in sys.argv[1:]:
        n = 0
        with gzip.GzipFile(gzfilename) as f:
            csv_file = csv.DictReader(f)
            first = True
            last_key = ''
            for row in csv_file:
                if first:
                    factory = ManagedCassandraClientFactory(row["keyspace"])
                    reactor.connectTCP("localhost", 9160, factory)
                    client = CassandraClient(factory)
                    first = False

                yield client.insert(column_family=row["cf"], key=uuidify(row["key"].decode("string_escape")), column=row["col"], value=uuidify(row["val"].decode("string_escape")))
                if last_key != row["key"].decode("string_escape"):
                    n += 1
                    last_key = row["key"].decode("string_escape")
            print "Successfully restored %d rows from %s" % (n, gzfilename)
    reactor.stop()

do_this()
reactor.run()
