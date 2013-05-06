#!/bin/bash

# @file do_backup.sh
#
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by post at
# Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK

die () {
  echo >&2 "$@"
  exit 1
}

[ "$#" -eq 1 ] || die "Usage: do_backup.sh <keyspace>"
KEYSPACE=$1
DATA_DIR=/var/lib/cassandra/data
[ -d "$DATA_DIR/$KEYSPACE" ] || die "Keyspace $KEYSPACE does not exist"

# Remove old backups (keeping last 3)
# Cassandra keeps snapshots per columnfamily, so we need to delete them individually
DIRS=$(find $DATA_DIR/$KEYSPACE/ -type d | grep 'snapshots$')
for d in $DIRS
do
  for f in $(ls -t $d | tail -n +4)
  do
    echo "Deleting old backup: $d/$f"
    rm -r $d/$f
  done
done

echo "Creating backup for keyspace $KEYSPACE..."
nodetool -h localhost -p 7199 snapshot $KEYSPACE
