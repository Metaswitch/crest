#! /bin/bash

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

if [[ ! -e /var/lib/cassandra/data/homestead_provisioning ]];
then
    echo "CREATE KEYSPACE homestead_provisioning WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
USE homestead_provisioning;
CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text, realm text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | $namespace_prefix cqlsh 
fi

echo "USE homestead_provisioning; DESC TABLE private" | cqlsh | grep plaintext_password > /dev/null
if [ $? != 0 ]; then
  echo "USE homestead_provisioning;
  ALTER TABLE private ADD plaintext_password text;" | $namespace_prefix cqlsh
fi
