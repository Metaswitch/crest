#!/bin/bash

# @file poll_homer.sh
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

# Grab our configuration
. /etc/clearwater/config

# Send HTTP request to normal/management interface and check that the response is "OK".
http_url=http://127.0.0.1:7888/ping
curl -f -g -m 2 -s $http_url 2> /tmp/poll-homer.sh.stderr.$$ | tee /tmp/poll-homer.sh.stdout.$$ | head -1 | egrep -q "^OK$"
rc=$?

# Check the return code and log if appropriate.
if [ $rc != 0 ] ; then
  echo HTTP failed to $http_url    >&2
  cat /tmp/poll-homer.sh.stderr.$$ >&2
  cat /tmp/poll-homer.sh.stdout.$$ >&2
fi
rm -f /tmp/poll-homer.sh.stderr.$$ /tmp/poll-homer.sh.stdout.$$

if [ ! -z $signaling_namespace ] ; then
  # For the signalling address, wrap IPv6 addresses in square brackets. This should be the local_ip.
  http_ip=$(/usr/share/clearwater/bin/bracket-ipv6-address $local_ip)
  /usr/share/clearwater/bin/poll-http $http_ip:7888
  rc_sig=$?

  [ $rc == 0 ] && [ $rc_sig == 0 ] ; rc=$?
fi

exit $rc
