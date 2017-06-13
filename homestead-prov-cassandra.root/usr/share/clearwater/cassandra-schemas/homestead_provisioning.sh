#! /bin/bash

cassandra_hostname="127.0.0.1"

. /etc/clearwater/config

. /usr/share/clearwater/cassandra_schema_utils.sh

quit_if_no_cassandra

echo "Adding/updating Cassandra schemas..."

count=0
/usr/share/clearwater/bin/poll_cassandra.sh --no-grace-period > /dev/null 2>&1

while [ $? -ne 0 ]; do
  ((count++))
  if [ $count -gt 120 ]; then
    echo "Cassandra isn't responsive, unable to add/update schemas yet"
    exit 1
  fi

  sleep 1
  /usr/share/clearwater/bin/poll_cassandra.sh --no-grace-period > /dev/null 2>&1
done

CQLSH="/usr/share/clearwater/bin/run-in-signaling-namespace cqlsh"

if [[ ! -e /var/lib/cassandra/data/homestead_provisioning ]] || \
   [[ $cassandra_hostname != "127.0.0.1" ]];
then
  # replication_str is set up by
  # /usr/share/clearwater/cassandra-schemas/replication_string.sh
  echo "CREATE KEYSPACE IF NOT EXISTS homestead_provisioning WITH REPLICATION = $replication_str;
USE homestead_provisioning;
CREATE TABLE IF NOT EXISTS implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE IF NOT EXISTS service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE IF NOT EXISTS public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE IF NOT EXISTS private (private_id text PRIMARY KEY, digest_ha1 text, realm text)
WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $CQLSH
fi

echo "USE homestead_provisioning; DESC TABLE private" | $CQLSH | grep plaintext_password > /dev/null
if [ $? != 0 ]; then
  echo "USE homestead_provisioning;
  ALTER TABLE private ADD plaintext_password text;" | $CQLSH
fi
