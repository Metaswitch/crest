#!/bin/bash
. /etc/clearwater/config

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

  # If local_site_name and remote_site_names are set then this is a GR
  # deployment. Set the replication strategy to NetworkTopologyStrategy and
  # define the sites.
  if [ -n $local_site_name ] && [ -n $remote_site_names ]
  then
    IFS=',' read -a remote_site_names_array <<< "$remote_site_names"
    replication_str="{'class': 'NetworkTopologyStrategy', '$local_site_name': 2"
    for remote_site in "${remote_site_names_array[@]}"
    do
      # Set the replication factor for each site to 2.
      replication_str+=", '$remote_site': 2"
    done
    replication_str+="}"
  fi

  echo "CREATE KEYSPACE homer WITH REPLICATION = $replication_str;
        USE homer;
        CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi
