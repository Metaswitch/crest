#!/bin/bash

set -e

num_users=${1:-50000}
top_number=$(expr 2010000000 + $num_users - 1)
numbers=$(seq 2010000000 $top_number)

filename=/tmp/$$.users.csv

. /etc/clearwater/config; for DN in $numbers ; do
echo sip:$DN@$home_domain,$DN@$home_domain,$home_domain,7kkzTyGW ;
done > $filename

echo "Creating $num_users users..."

/usr/share/clearwater/crest-prov/src/metaswitch/crest/tools/bulk_create.py $filename > /dev/null 2>&1
/tmp/$$.users.create_homestead.sh > /dev/null 2>&1

echo "Created $num_users users"

rm /tmp/$$.users.*
