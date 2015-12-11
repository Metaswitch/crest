#! /bin/bash
. /etc/clearwater/config

if [[ ! -e /var/lib/cassandra/data/homestead_provisioning ]];
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

  echo "CREATE KEYSPACE homestead_provisioning WITH REPLICATION = $replication_str;
USE homestead_provisioning;
CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text, realm text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh
fi

echo "USE homestead_provisioning; DESC TABLE private" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh | grep plaintext_password > /dev/null
if [ $? != 0 ]; then
  echo "USE homestead_provisioning;
  ALTER TABLE private ADD plaintext_password text;" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh
fi
