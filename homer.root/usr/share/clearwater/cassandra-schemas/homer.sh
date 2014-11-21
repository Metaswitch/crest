#!/bin/bash

header="Waiting for Cassandra"
let "cnt=0"
netstat -na | grep -q ":7199[^0-9]"
while [ $? -ne 0 ]; do
    sleep 1
    printf "${header}."
    header=""
    let "cnt=$cnt + 1"
    if [ $cnt -gt 120 ]; then
	printf "*** ERROR: Cassandra did not come online!\n"
	exit 1
    fi
    netstat -na | grep -q ":7199[^0-9]"
done
let "cnt=0"
netstat -na | grep "LISTEN" | awk '{ print $4 }' | grep -q ":9160\$"
while [ $? -ne 0 ]; do
    sleep 1
    printf "${header}+"
    header=""
    let "cnt=$cnt + 1"
    if [ $cnt -gt 120 ]; then
	printf "*** ERROR: Cassandra did not come online!\n"
	exit 1
    fi
    netstat -na | grep "LISTEN" | awk '{ print $4 }' | grep -q ":9160\$"
done

if [[ ! -e /var/lib/cassandra/data/homer ]];
then
    echo "CREATE KEYSPACE homer WITH strategy_class='org.apache.cassandra.locator.SimpleStrategy' AND strategy_options:replication_factor=2;
USE homer;
CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH read_repair_chance = 1.0;" | cqlsh -2
fi
