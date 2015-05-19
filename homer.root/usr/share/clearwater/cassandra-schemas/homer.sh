#!/bin/bash

. /etc/clearwater/config
if [ ! -z $signaling_namespace ]
then
  if [ $EUID -ne 0 ]
  then
    echo "When using multiple networks, schema creation must be run as root"
    exit 2
  fi
  namespace_prefix="ip netns exec $signaling_namespace"
fi

if [[ ! -e /var/lib/cassandra/data/homer ]];
then
  header="Waiting for Cassandra"
  let "cnt=0"
  $namespace_prefix netstat -na | grep -q ":7199[^0-9]"
  while [ $? -ne 0 ]; do
    sleep 1
    printf "${header}."
    header=""
    let "cnt=$cnt + 1"
    if [ $cnt -gt 120 ]; then
      printf "*** ERROR: Cassandra did not come online!\n"
      exit 1
    fi
    $namespace_prefix netstat -na | grep -q ":7199[^0-9]"
  done
  let "cnt=0"
  $namespace_prefix netstat -na | grep "LISTEN" | awk '{ print $4 }' | grep -q ":9160\$"
  while [ $? -ne 0 ]; do
    sleep 1
    printf "${header}+"
    header=""
    let "cnt=$cnt + 1"
    if [ $cnt -gt 120 ]; then
      printf "*** ERROR: Cassandra did not come online!\n"
      exit 1
    fi
    $namespace_prefix netstat -na | grep "LISTEN" | awk '{ print $4 }' | grep -q ":9160\$"
  done

  echo "CREATE KEYSPACE homer WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
        USE homer;
        CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi
