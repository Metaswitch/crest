#!/bin/bash

if [[ ! -e /var/lib/cassandra/data/homer ]];
then
  count=0
  /usr/share/clearwater/bin/poll_cassandra.sh --no-grace-period

  while [ $? -ne 0 ]; do
    ((count++))
    if [ $count -gt 120 ]; then
      echo "Cassandra isn't responsive, unable to add schemas"
      exit 1
    fi

    sleep 1
    /usr/share/clearwater/bin/poll_cassandra.sh --no-grace-period
  done

  echo "CREATE KEYSPACE homer WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
        USE homer;
        CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi
