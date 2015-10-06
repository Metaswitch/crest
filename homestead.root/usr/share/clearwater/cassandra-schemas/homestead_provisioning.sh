#! /bin/bash

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

  echo "CREATE KEYSPACE homestead_provisioning WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
USE homestead_provisioning;
CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text, realm text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh 
fi

echo "USE homestead_provisioning; DESC TABLE private" | cqlsh | grep plaintext_password > /dev/null
if [ $? != 0 ]; then
  echo "USE homestead_provisioning;
  ALTER TABLE private ADD plaintext_password text;" | /usr/share/clearwater/bin/run-in-signaling-namespace cqlsh
fi
