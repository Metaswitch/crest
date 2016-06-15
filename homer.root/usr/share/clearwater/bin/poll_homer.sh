#!/bin/bash

# @file poll_homer.sh
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2014  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version, along with the "Special Exception" for use of
# the program along with SSL, set forth below. This program is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details. You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by
# post at Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK
#
# Special Exception
# Metaswitch Networks Ltd  grants you permission to copy, modify,
# propagate, and distribute a work formed by combining OpenSSL with The
# Software, or a work derivative of such a combination, even if such
# copying, modification, propagation, or distribution would otherwise
# violate the terms of the GPL. You must comply with the GPL in all
# respects for all of the code used other than OpenSSL.
# "OpenSSL" means OpenSSL toolkit software distributed by the OpenSSL
# Project and licensed under the OpenSSL Licenses, or a work based on such
# software and licensed under the OpenSSL Licenses.
# "OpenSSL Licenses" means the OpenSSL License and Original SSLeay License
# under which the OpenSSL Project distributes the OpenSSL toolkit software,
# as those licenses appear in the file LICENSE-OPENSSL.

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
