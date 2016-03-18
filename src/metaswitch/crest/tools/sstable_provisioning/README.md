# Clearwater Bulk Provisioning

These scripts will enable you to create a collection of sstables (Cassandra raw data) and then inject those tables directly into your Cassandra cluster.

All the scripts assume they are being run on a Homer or Homestead node with a correctly configured and balanced Cassandra cluster.

## Pre-requisites

* The bulk provisioning binaries - automatically installed alongside Homer/Homestead to `/usr/share/clearwater/crest/tools/sstable_provisioning`
* A users CSV file - In the format output by [`bulk_autocomplete.py`](https://github.com/Metaswitch/crest/blob/dev/docs/Bulk-Provisioning%20Numbers.md)

## Disk space

This process uses a fair amount of disk space (25M subscribers uses 110Gb).  If you do not have enough space on your primary hard drive, copy the contents of the sstable_provisioning folder to a larger partition and run all the commands listed below from there.

_For example, on AWS, instances have ony ~4Gb free so we can only provision approx 1M subscribers this way.  To provision more, copy this folder to `/mnt` and run the commands from there._

## RAM

The [Preparing the sstables](#preparing-the-sstables) step also uses quite a lot of RAM.  If you're running on a homestead or homer node, Cassandra will already be using a lot of the node's RAM.  For improved performance, you can stop Cassandra for the duration of that step and restart it again afterwards.  This obviously causes a service outage, and so should only be used for bulk provisioning as part of initial turn-up!  To stop Cassandra, run `sudo monit stop cassandra` and to restart it run `sudo monit start cassandra`.

## Preparing the sstables

The sstables can be created either from CSV files describing each subscriber or from command-line parameters specifying a range.  The latter is better for setting up stress runs (where you often want all your subscribers to be the same anyway) - the former is better for real subscribers. In each case, start by running

    cd /usr/share/clearwater/crest/tools/sstable_provisioning

### From CSV

In the below, `<csvfilename>` refers to the filename of the users CSV file **without the suffix**, e.g. if the file were called `users.csv` then `<csvfilename>` would be `users`.

Use the python executable bundled with Homer/Homestead.

    export PATH=/usr/share/clearwater/crest/env/bin:$PATH

Prepare the CSV file by hashing the password and adding the simservs/ifc bodies.

    python ./prepare_csv.py <csvfilename>.csv

This will generate `<csvfilename>_prepared.csv` in the current folder.  This filename should now be passed to BulkProvision as a command-line parameter, e.g. as follows - see more detail below.

    sudo ./BulkProvision homestead-local <csvfilename>_prepared.csv

To store the passwords for the subscribers (in plaintext), add the `plaintext_password` parameter, e.g.:

    sudo ./BulkProvision homestead-local <csvfilename>_prepared.csv plaintext_password


### From a range

To create sstables for a range of subscribers, all with identical configuration, pass the following parameters to BulkProvision.

*   start directory number
*   end directory number
*   domain
*   password

For example, to create sstables for running clearwater-sip-stress stress tests with 1 million subscribers, the parameters might be as follows - see more detail below.

    sudo ./BulkProvision homestead-local 2010000000 2010999999 example.com 7kkzTyGW

To store the passwords for the subscribers (in plaintext), add the `plaintext_password` parameter, e.g.:

    sudo ./BulkProvision homestead-local 2010000000 2010999999 example.com 7kkzTyGW plaintext_parameter

### Running BulkProvision

Now that you've got the parameters, run one of the following commands.

    sudo ./BulkProvision homer <parameters>
    sudo ./BulkProvision homestead-local <parameters>
    sudo ./BulkProvision homestead-hss <parameters>
    sudo ./BulkProvision memento <parameters>

This will create one or more new directories containing various sstable files for that node type:

* `homer` creates a single directory called homer
* `memento` creates a single directory called memento
* `homestead-local` generates both homestead\_cache and homestead\_provisioning directories, to simulate use of the local provisioning API.
* `homestead-hss` only produces the homestead\_cache directory, to simulate use of an external HSS.

## Injecting the sstables

To inject the data into the current cluster run:

_For homer:_

    . /etc/clearwater/config
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homer/simservs

_For homestead:_

    . /etc/clearwater/config
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_cache/impi
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_cache/impu
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_provisioning/implicit_registration_sets
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_provisioning/public
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_provisioning/private
    sstableloader -v -d ${cassandra_hostname:-$local_ip} homestead_provisioning/service_profiles

_For memento:_

    . /etc/clearwater/config
    sstableloader -v -d ${cassandra_hostname:-$local_ip} memento/call_lists
