#!/bin/bash

# @file restore_backup.sh
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

[ "$#" -ge 1 ] || die "Usage: restore_backup.sh <keyspace> <backup> (will default to latest backup if none specified)"
KEYSPACE=$1
BACKUP=$2
DATA_DIR=/var/lib/cassandra/data
COMMITLOG_DIR=/var/lib/cassandra/commitlog

if [[ -z "$BACKUP" ]]
then
  echo "No backup specified, will attempt to backup from latest"
else
  echo "Will attempt to backup from backup $BACKUP"
fi

# Cassandra keeps snapshots per columnfamily, so we need to restore them individually
for d in $DATA_DIR/$KEYSPACE/*
do
  cd $d
  
  # First make sure we have a backup to backup from
  if [ -d "snapshots" ]
  then
    if [[ -z $BACKUP ]]
    then
      echo "No valid backup specified, will attempt to backup from latest"
      BACKUP=$(ls -t snapshots | head -1)
    elif [ -d "snapshots/$BACKUP" ]
    then
      echo "Found backup directory $BACKUP"
    else
      die "Could not find specified backup directory for columnfamily $d, use list_backups to see available backups"
    fi 
  else
    die "Snapshot directory does not exist for columnfamily $d"
  fi
done

# We've made sure all the necessary backups exist, proceed with backup
[ -d "$DATA_DIR/$KEYSPACE" ] || die "Keyspace $KEYSPACE does not exist"
echo "Restoring backup for keyspace $KEYSPACE..."

# Stop monit from restarting Cassandra while we restore
monit stop cassandra 
service cassandra stop

echo "Clearing commitlog..."
rm -rf $COMMITLOG_DIR/*

for d in $DATA_DIR/$KEYSPACE/*
do
  cd $d
  echo "Deleting old .db files..."
  find . -maxdepth 1 -type f -exec rm -rf {} \;
  echo "Restoring from backup: $BACKUP"
  sudo -u cassandra cp snapshots/$BACKUP/* .
done

monit start cassandra || service cassandra start
