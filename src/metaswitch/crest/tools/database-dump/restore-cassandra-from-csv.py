#! /usr/bin/python

"""Restores the gzipped CSV files given on the command line (created with dump-cassandra-to-csv.py) into the Cassandra database. Invoked with './restore-cassandra-from-csv.py file1.csv.gz file2.csv.gz ...' """

from twisted.internet import defer, reactor
from telephus.protocol import ManagedCassandraClientFactory
from telephus.client import CassandraClient, ConsistencyLevel
import telephus
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
