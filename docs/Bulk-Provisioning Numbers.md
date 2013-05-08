Bulk-Provisioning Numbers
=========================

To bulk-provision numbers, follow the following process.

1.  Create a CSV file with one row per number, and the following
    columns. (If you want to quickly create a contiguous range, you can
    use something like `for DN in {2010000000..2010099999} ; do echo sip:$DN@cw-ngv.com ; done`.)
    1.  Public SIP ID (mandatory)
    2.  Private SIP ID (optional, defaults to public SIP ID, stripping
        any sip: prefix)
    3.  Realm (optional, defaults to system default)
    4.  Password (optional, defaults to auto-generated random password)

2.  Copy it onto a homestead node.
3.  Log into the homestead node.
4.  If you ommitted any columns,
    1.  run
        /usr/share/clearwater/homestead/src/metaswitch/crest/tools/bulk\_autocomplete.py
        - this will fill in any missing columns, as described above
    2.  take a copy of this file, as you will need the passwords later
        to log your phone(s) in.

5.  Run
    /usr/share/clearwater/homestead/src/metaswitch/crest/tools/bulk\_create.py
    - this will create 4 files - 2 \*.create\_homestead.\* files and 2
    \*.create\_xdm.\* files.
6.  Run the resulting \*.create\_homestead.sh script on the homestead
    node.
7.  Copy the \*.create\_xdm.\* files to a homer node and run the
    \*.create\_xdm.sh script there, as instructed.

