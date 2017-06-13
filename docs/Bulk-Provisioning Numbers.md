# Bulk-Provisioning Numbers

## Stress

If you are provisioning numbers for SIPp stress testing, we've produced a simple process for this - just run the following script on any Homestead Cassandra node:

```
/usr/share/clearwater/crest-prov/src/metaswitch/crest/tools/stress_provision.sh
```

This provisions numbers starting at 201000000 with the password 7kkzTyGW, and will provision 50,000 users by default, which takes around 15 minutes - to provision a different number, just pass it in as an argument:

```
/usr/share/clearwater/crest-prov/src/metaswitch/crest/tools/stress_provision.sh 200000
```

This will only provision data into Homestead's call-path cache, for efficiency - if you need Homer, Memento or Homestead-prov provisioning, follow the process below.

## Other uses

To bulk-provision numbers in a more flexible way, follow the following process.  (There is an alternative bulk provisioning process documented [here] (https://github.com/Metaswitch/crest/blob/dev/src/metaswitch/crest/tools/sstable_provisioning/README.md) - while this is more complex to set up, it may be more suitable if you are provisioning very large sets of numbers.)

1.  Log into any Homestead Cassandra node in your deployment.
2.  Create a CSV file with one row per number, and the following
    columns. (If you want to quickly create a contiguous range, you can
    use something like `. /etc/clearwater/config; for DN in {2010000000..2010099999} ; do echo sip:$DN@$home_domain ; done > users.csv`.)
    1.  Public SIP ID (mandatory)
    2.  Private SIP ID (optional, defaults to public SIP ID, stripping any sip: prefix)
    3.  Realm (optional, defaults to domain of public SIP ID)
    4.  Password (optional, defaults to auto-generated random password)
3.  If you omitted any columns,
    1.  run
        /usr/share/clearwater/crest-prov/src/metaswitch/crest/tools/bulk\_autocomplete.py users.csv
        - this will fill in any missing columns, as described above
    2.  take a copy of this file, as you will need the passwords later
        to log your phone(s) in.

4.  Run
    `/usr/share/clearwater/crest-prov/src/metaswitch/crest/tools/bulk_create.py users.csv` (or `users.auto.csv` if you used bulk\_autocomplete.py). If you need example call list data add the `--memento` option. If you want to store the passwords (in plaintext) of the subscribers add the `--plaintext_password` option. This will create a number of files in the current directory.
5.  Run the resulting \*.create\_homestead.sh script on the Homestead Cassandra node.
6.  Copy the \*.create\_xdm.\* files to a Homer Cassandra node and run the \*.create\_xdm.sh script there, as instructed.
7.  If you need call list data, copy the \*.create\_memento.\* files to a memento node and run the \*create\_memento.sh script there, as instructed.

