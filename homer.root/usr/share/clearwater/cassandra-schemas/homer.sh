#!/bin/bash

cassandra_installed=$(dpkg-query -W -f='${Status}\n' cassandra | grep -q "install ok installed")

if [[ ! $cassandra_installed ]]
then
  echo "Cassandra is not installed yet, skipping schema addition for now"
  exit 0
fi

. /usr/share/clearwater/cassandra-schemas/replication_string.sh

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

  replication_str="{'class': 'SimpleStrategy', 'replication_factor': 2}"

  # replication_str is set up by
  # /usr/share/clearwater/cassandra-schemas/replication_string.sh
  echo "CREATE KEYSPACE homer WITH REPLICATION = $replication_str;
        USE homer;
        CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh
fi
