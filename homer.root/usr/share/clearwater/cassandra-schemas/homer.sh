#!/bin/bash
if [[ ! -e /var/lib/cassandra/data/homer ]];
then
    echo "CREATE KEYSPACE homer WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
USE homer;
CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH read_repair_chance = 1.0;" | cqlsh -3
fi
