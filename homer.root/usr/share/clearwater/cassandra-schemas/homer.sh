#!/bin/bash

cassandra_hostname="127.0.0.1"

. /usr/share/clearwater/cassandra_schema_utils.sh

quit_if_no_cassandra

CQLSH="/usr/share/clearwater/bin/run-in-signaling-namespace cqlsh $cassandra_hostname"

if [[ ! -e /var/lib/cassandra/data/homer ]] || \
   [[ $cassandra_hostname != "127.0.0.1" ]];
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

  replication_str="{'class': 'SimpleStrategy', 'replication_factor': 2}"

  # replication_str is set up by
  # /usr/share/clearwater/cassandra-schemas/replication_string.sh
  echo "CREATE KEYSPACE homer WITH REPLICATION = $replication_str;
        USE homer;
        CREATE TABLE simservs (user text PRIMARY KEY, value text)
        WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $CQLSH
fi
