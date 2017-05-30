#! /usr/bin/python

# Copyright (C) Metaswitch Networks 2014
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

"""Backs up all data in the given keyspaces to a gzipped CSV file (one file per column family). Invoked with 'dump-cassandra-to-csv.py keyspace1 keyspace2...'"""

from twisted.internet import defer, reactor
from telephus.protocol import ManagedCassandraClientFactory
from telephus.client import CassandraClient
import gzip
import csv
import sys
keyspaces = sys.argv[1:]

@defer.inlineCallbacks
def do_this():
    for keyspace in keyspaces:
        factory = ManagedCassandraClientFactory(keyspace)
        reactor.connectTCP("localhost", 9160, factory)
        client = CassandraClient(factory)
        k =  yield client.describe_keyspace(keyspace)
        for cf in [c.name for c in k.cf_defs]:
            n = 0
            db_rows = yield client.get_range_slices(column_family=cf, count=10000000)
            with gzip.GzipFile("%s.%s.csv.gz" % (keyspace, cf), "w") as f:
                out = csv.DictWriter(f, fieldnames=["keyspace", "cf", "key", "col", "val"])
                out.writeheader()
                for row in db_rows:
                    for col in row.columns:
                        out.writerow({"keyspace": keyspace,
                                      "cf": cf,
                                      "key": row.key.encode("string_escape"),
                                      "col": col.column.name,
                                      "val": col.column.value.encode("string_escape")})
                    n += 1
                print "Successfully backed up %d rows from %s.%s" % (n, keyspace, cf)
    reactor.stop()


do_this()
reactor.run()
