#!/bin/bash

# @file poll_homestead-prov.sh
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


# Send HTTP request and check that the response is "OK".
http_url=http://127.0.0.1:8889/ping
curl -f -g -m 2 -s $http_url 2> /tmp/poll-homestead_prov.sh.stderr.$$ | tee /tmp/poll-homestead_prov.sh.stdout.$$ | head -1 | egrep -q "^OK$"
rc=$?

# Check the return code and log if appropriate.
if [ $rc != 0 ] ; then
  echo HTTP failed to $http_url             >&2
  cat /tmp/poll-homestead_prov.sh.stderr.$$ >&2
  cat /tmp/poll-homestead_prov.sh.stdout.$$ >&2
fi
rm -f /tmp/poll-homestead_prov.sh.stderr.$$ /tmp/poll-homestead_prov.sh.stdout.$$

exit $rc
