#! /bin/bash

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

if [[ ! -e /var/lib/cassandra/data/homestead_provisioning ]];
then
    echo "CREATE KEYSPACE homestead_provisioning WITH strategy_class='org.apache.cassandra.locator.SimpleStrategy' AND strategy_options:replication_factor=2;
USE homestead_provisioning;
CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH read_repair_chance = 1.0;
CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH read_repair_chance = 1.0;
CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH read_repair_chance = 1.0;
CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text) WITH read_repair_chance = 1.0;" | cqlsh -2
fi
echo "USE homestead_provisioning;
ALTER TABLE private ADD realm text;" | cqlsh -2
