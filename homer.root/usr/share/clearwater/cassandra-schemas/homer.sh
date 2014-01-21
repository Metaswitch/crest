#!/bin/bash
if [[ ! -e /var/lib/cassandra/data/homer ]];
then
    echo "CREATE KEYSPACE homer WITH strategy_class='org.apache.cassandra.locator.SimpleStrategy' AND strategy_options:replication_factor=2;
USE homer;
CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH read_repair_chance = 1.0;" | cqlsh -2
fi
