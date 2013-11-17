# Clearwater Bulk Provisioning

These scripts will enable you to create a collection of sstables (Cassandra raw data) and then inject those tables directly into your Cassandra cluster.

All the scripts assume they are being run on a homer or homestead node with a correctly configured and balanced Cassandra cluster.

## Pre-requisites

* This code - Automatically installed alongside homer/homestead to 

        /usr/share/clearwater/<role>/src/metaswitch/crest/tools/sstable_provisioning/

* `make` - `sudo apt-get install make`
* `javac` - `sudo apt-get install openjdk-6-jdk`
* `python` - Installed with homer/homestead
* `/etc/cassandra/cassandra.yaml` - Installed during clustering
* `/usr/share/cassandra/*` - Installed with dsc1.1
* Users CSV file - In the format output by `bulk_autocomplete.py`

## Disk space

This process uses a fair amount of disk space (25M subscribers uses 110Gb).  If you do not have enough space on your primary hard drive, copy the contents of the sstable_provisioning folder to a larger partition and run all the commands listed below from there.

_For example, on AWS, instances have ony ~4Gb free so we can only provision approx 1M subscribers this way.  To provision more, copy this folder to `/mnt` and run the commands from there._

## RAM

The [Preparing the sstables](#preparing-the-sstables) step also uses quite a lot of RAM.  If you're running on a homestead or homer node, Cassandra will already be using a lot of the node's RAM.  For improved performance, you can stop Cassandra for the duration of that step and restart it again afterwards.  This obviously causes a service outage, and so should only be used for bulk provisioning as part of initial turn-up!  To stop Cassandra, run `sudo monit stop cassandra` and to restart it run `sudo monit start cassandra`.

## Binary compilation

    make

This will compile the ClearwaterBulkProvisioner classes.  If the compiler cannot find the imported classes, ensure cassandra is correctly installed on your machine.

## Preparing the sstables

In the below, `<csvfilename>` refers to the filename of the users CSV file **without the suffix**, e.g. if the file were called `users.csv` then `<csvfilename>` would be `users`.

Use the python executable bundled with homer/homestead.

    export PATH=/usr/share/clearwater/homer/env/bin:$PATH
    export PATH=/usr/share/clearwater/homestead/env/bin:$PATH

Prepare the CSV file by hashing the password and adding the simservs/ifc bodies.

    python ./prepare_csv.py <csvfilename>.csv

This will generate `<csvfilename>_prepared.csv` in the current folder.  This should now be converted into sstables with one of the following

    sudo ./BulkProvision <csvfilename>_prepared.csv homer
    sudo ./BulkProvision <csvfilename>_prepared.csv homestead-local
    sudo ./BulkProvision <csvfilename>_prepared.csv homestead-hss

This will create a `homer` or `homestead_cache` and `homestead_provisioning` folders in the current directory which will contain the various sstable files for that node type.  `homestead-local` will generate both homestead_cache and homestead_provisioning directories, to simulate use of the local provisioning API.  `homestead-cache` will only produce the homestead_cache directory, to simulate use of an external HSS.

## Injecting the sstables

To inject the data into the current cluster run:

_For homer:_

    . /etc/clearwater/config
    sstableloader -v -d $local_ip homer/simservs

_For homestead:_

    . /etc/clearwater/config
    sstableloader -v -d $local_ip homestead_cache/impi
    sstableloader -v -d $local_ip homestead_cache/impu
    sstableloader -v -d $local_ip homestead_provisioning/irs
    sstableloader -v -d $local_ip homestead_provisioning/public
    sstableloader -v -d $local_ip homestead_provisioning/private
