#!/bin/bash

# @file do_backup.sh
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2013  Metaswitch Networks Ltd
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

die () {
  echo >&2 "$@"
  exit 1
}

[ "$#" -eq 1 ] || die "Usage: do_backup.sh <keyspace>"
KEYSPACE=$1
DATA_DIR=/var/lib/cassandra/data
BACKUP_DIR="/usr/share/clearwater/$1/backup/backups"
[ -d "$DATA_DIR/$KEYSPACE" ] || die "Keyspace $KEYSPACE does not exist"
if [[ ! -d "$BACKUP_DIR" ]]
then
  mkdir -p $BACKUP_DIR
  echo "Created backup directory $BACKUP_DIR"
fi

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

for f in $(ls -t $BACKUP_DIR | tail -n +4)
do
  echo "Deleting old backup: $BACKUP_DIR/$f"
  rm -r $BACKUP_DIR/$f
done

echo "Creating backup for keyspace $KEYSPACE..."
nodetool -h localhost -p 7199 snapshot $KEYSPACE

for t in $DATA_DIR/$KEYSPACE/*
do
  TABLE=`basename $t`
  for s in $DATA_DIR/$KEYSPACE/$TABLE/snapshots/*
  do
    SNAPSHOT=`basename $s`
    mkdir -p $BACKUP_DIR/$SNAPSHOT/$TABLE
    cp -al $DATA_DIR/$KEYSPACE/$TABLE/snapshots/$SNAPSHOT/* $BACKUP_DIR/$SNAPSHOT/$TABLE
  done
done

echo "Backups can be found at: $BACKUP_DIR"
