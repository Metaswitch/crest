## Clearwater - Cassandra database dump scripts

This directory contains Python scripts to dump and restore Cassandra keyspaces to/from CSV files. It is slower and more network-intensive than the ordinary process (described at https://github.com/Metaswitch/clearwater-docs/wiki/Backups), but dumps created by this method can be restored onto a Cassandra cluster of a different version or a different size, unlike the backups created by the ordinary process.

## Usage

This directory contains two files:

`dump-cassandra-to-csv.py` takes a list of keyspaces as its arguments and dumps those out to a series of gzipped CSV files.

`restore-cassandra-from-csv.py` takes a list of gzipped CSV files as its arguments, and injects those into the local Cassandra database. It expects the necessary schemas to already exist, so those will have to be restored through other means (such as a reinstall of the Homer/Homestead packages).

## Examples

### Homer

```
[homer-1]ubuntu:~$ /usr/share/clearwater/homer/env/bin/python dump-cassandra-to-csv.py homer
/usr/share/clearwater/homer/env/local/lib/python2.7/site-packages/zope.interface-4.0.5-py2.7-linux-x86_64.egg/zope/__init__.py:3: UserWarning: Module twisted was already imported from /usr/share/clearwater/homer/env/local/lib/python2.7/site-packages/Twisted-12.3.0-py2.7-linux-x86_64.egg/twisted/__init__.pyc, but /usr/share/clearwater/homer/env/lib/python2.7/site-packages/cyclone-1.0-py2.7.egg is being added to sys.path
  import pkg_resources
Successfully backed up 10004 rows from homer.simservs
[homer-1]ubuntu:~$ ls *.csv.gz
homer.simservs.csv.gz
[homer-1]ubuntu:~$ /usr/share/clearwater/homer/env/bin/python restore-cassandra-from-csv.py *.csv.gz
/usr/share/clearwater/homer/env/local/lib/python2.7/site-packages/zope.interface-4.0.5-py2.7-linux-x86_64.egg/zope/__init__.py:3: UserWarning: Module twisted was already imported from /usr/share/clearwater/homer/env/local/lib/python2.7/site-packages/Twisted-12.3.0-py2.7-linux-x86_64.egg/twisted/__init__.pyc, but /usr/share/clearwater/homer/env/lib/python2.7/site-packages/cyclone-1.0-py2.7.egg is being added to sys.path
  import pkg_resources
Successfully restored 10001 rows from homer.simservs.csv.gz
[homer-1]ubuntu:~$
```

### Homestead

```
[homestead-1]ubuntu:~$ /usr/share/clearwater/homestead/env/bin/python dump-cassandra-to-csv.py homestead_cache homestead_provisioning
/usr/share/clearwater/homestead/env/local/lib/python2.7/site-packages/zope.interface-4.0.5-py2.7-linux-x86_64.egg/zope/__init__.py:3: UserWarning: Module twisted was already imported from /usr/share/clearwater/homestead/env/local/lib/python2.7/site-packages/Twisted-12.3.0-py2.7-linux-x86_64.egg/twisted/__init__.pyc, but /usr/share/clearwater/homestead/env/lib/python2.7/site-packages/cyclone-1.0-py2.7.egg is being added to sys.path
  import pkg_resources
Successfully backed up 10003 rows from homestead_cache.impi
Successfully backed up 10004 rows from homestead_cache.impu
Successfully backed up 10005 rows from homestead_provisioning.service_profiles
Successfully backed up 10004 rows from homestead_provisioning.public
Successfully backed up 10004 rows from homestead_provisioning.implicit_registration_sets
Successfully backed up 10003 rows from homestead_provisioning.private
[homestead-1]ubuntu:~$ ls *.csv.gz
homestead_cache.impi.csv.gz
homestead_cache.impu.csv.gz
homestead_provisioning.implicit_registration_sets.csv.gz
homestead_provisioning.private.csv.gz
homestead_provisioning.public.csv.gz
homestead_provisioning.service_profiles.csv.gz
[homestead-1]ubuntu:~$ /usr/share/clearwater/homestead/env/bin/python restore-cassandra-from-csv.py *.csv.gz
/usr/share/clearwater/homestead/env/local/lib/python2.7/site-packages/zope.interface-4.0.5-py2.7-linux-x86_64.egg/zope/__init__.py:3: UserWarning: Module twisted was already imported from /usr/share/clearwater/homestead/env/local/lib/python2.7/site-packages/Twisted-12.3.0-py2.7-linux-x86_64.egg/twisted/__init__.pyc, but /usr/share/clearwater/homestead/env/lib/python2.7/site-packages/cyclone-1.0-py2.7.egg is being added to sys.path
  import pkg_resources
Successfully restored 10001 rows from homestead_cache.impi.csv.gz
Successfully restored 10001 rows from homestead_cache.impu.csv.gz
Successfully restored 10004 rows from homestead_provisioning.implicit_registration_sets.csv.gz
Successfully restored 10001 rows from homestead_provisioning.private.csv.gz
Successfully restored 10001 rows from homestead_provisioning.public.csv.gz
Successfully restored 10005 rows from homestead_provisioning.service_profiles.csv.gz
[homestead-1]ubuntu:~$
```
