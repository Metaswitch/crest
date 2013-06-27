Bulk-Provisioning Numbers
=========================

To bulk-provision numbers, follow the following process.

1.  Log into any homestead node in your deployment.
2.  Create a CSV file with one row per number, and the following
    columns. (If you want to quickly create a contiguous range, you can
    use something like `. /etc/clearwater/config; for DN in {2010000000..2010099999} ; do echo sip:$DN@$home_domain ; done > users.csv`.)
    1.  Public SIP ID (mandatory)
    2.  Private SIP ID (optional, defaults to public SIP ID, stripping
        any sip: prefix)
    3.  Realm (optional, defaults to system default)
    4.  Password (optional, defaults to auto-generated random password)

    If you are provisioning numbers for SIPp stress testing, you will need to force them all to use the password '7kkzTyGW'. This CSV file can be generated with
    ```
    . /etc/clearwater/config; for DN in {2010000000..2010099999} ; do
echo sip:$DN@$home_domain,$DN@$home_domain,$home_domain,7kkzTyGW ;
done > users.csv
```
    Increase the DN range as required to generate 100,000 subscribers per SIPp node.
3.  If you omitted any columns,
    1.  run
        /usr/share/clearwater/homestead/src/metaswitch/crest/tools/bulk\_autocomplete.py users.csv
        - this will fill in any missing columns, as described above
    2.  take a copy of this file, as you will need the passwords later
        to log your phone(s) in.

4.  Run
    /usr/share/clearwater/homestead/src/metaswitch/crest/tools/bulk\_create.py users.csv (or users.auto.csv if you used bulk\_autocomplete.py)
    - This will create four files - two \*.create\_homestead.\* files and two \*.create\_xdm.\* files.
5.  Run the resulting \*.create\_homestead.sh script on the homestead
    node.
6.  Copy the \*.create\_xdm.\* files to a homer node and run the
    \*.create\_xdm.sh script there, as instructed.

