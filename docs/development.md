Crest - Development Guide
===========

These instructions have been tested on Ubuntu 14.04, using Python version 2.7.3.

Get the code
============

    git clone --recursive git@github.com:Metaswitch/crest.git

This accesses the repository over SSH on GitHub, and will not work unless you have a GitHub account and registered SSH key. If you do not have both of these, you will need to configure Git to read over HTTPS instead:

    git config --global url."https://github.com/".insteadOf git@github.com:
    git clone --recursive git@github.com:Metaswitch/crest.git

The code consists of the `crest` repository and its submodules as
defined in `.gitmodules`:

* `python-common`, which appears at `modules/common/`, contains Python utility
  code shared between the Python components of Clearwater.
* `clearwater-build-infra`, which appears at `build-infra/`, contains
  support for building Debian packages which is shared between all
  components of Clearwater.
* `pure-sasl`, which appears at `modules/pure-sasl/`, a Python SASL implementation
* `sdp`, which appears at `modules/sdp/`, a Python diameter stack
* `telephus`, which appears at `modules/telephus/`, a Twisted Cassandra API

Pre-requisites
==============

Crest relies on APT packages available from the Project Clearwater repository server. To configure your build environment to install these packages, follow the instructions at [ReadTheDocs](http://clearwater.readthedocs.org/en/latest/Manual_Install.html#configure-the-apt-software-sources).

1. Pip and build tools

    ```
    sudo apt-get install python-pip python-dev build-essential libffi-dev
    ```

2. virtualenv (we pin to 13.1.0 so that we have a known working version, but we should be careful that the version used doesn't fall too far behind)

   ```
   sudo pip install virtualenv==13.1.0
   ```

3. Lib-curl

    ```
    sudo apt-get install libcurl4-openssl-dev
    ```

4. Building Debian packages

    ```
    sudo apt-get install debhelper devscripts
    ```

5. XML development libraries

    ```
    sudo apt-get install libxml2-dev libxslt-dev
    ```

6. Python static analysis checker

   ```
   sudo pip install flake8 mccabe pep8-naming
   ```

7. ZMQ libraries

   ```
   sudo apt-get install python-zmq
   ```

8. Bulk provisioning

   ```
   sudo apt-get install cassandra=2.1.15 openjdk-7-jdk
   ```
   This cassandra version is available from the Project Clearwater repo server.
   See the Clearwater Readthedocs Manual Install instructions for detail on how
   to install debians from this server.

Setting up a virtualenv
=======================

The main language of the project is Python. virtualenv is used to create a
virtual Python environment in a subfolder containing only the required
dependencies, at the expected versions. To create the virtualenv environment,
change to the crest directory checked out from git and then execute:

    make env

As part of the environment, a special Python executable is generated in the
`bin/` subdirectory.  That executable is preconfigured to use the correct
PYTHONPATH to pick up the dependencies in the env directory. Whenever you run
crest or its tools, be sure to use this, rather than the system Python.

Local settings
==============

It's useful to override the default settings of the project for local debugging.
To avoid accidentally checking in such changes, the settings module loads a local
override file from `src/metaswitch/crest/local_settings.py`.  The file is
executed in the context of `settings.py` after `settings.py` completes.  Anything
that could be put at the bottom of `settings.py` can be put in `local_settings.py`.

For Homestead-prov, you'll probably need at least the following in
`local_settings.py` (replacing `example.com` with the correct domain).

    LOG_FILE_PREFIX = "homestead-prov"
    PROCESS_NAME = "homestead-prov"
    INSTALLED_HANDLERS = ["homestead"]
    HTTP_PORT = 8889
    HSS_ENABLED = False
    SIP_DIGEST_REALM = "example.com"
    HTTP_UNIX = "/tmp/.homestead-prov-sock"

For a Homer node, you'll probably need the following instead.

    LOG_FILE_PREFIX = "homer"
    PROCESS_NAME = "homer"
    INSTALLED_HANDLERS = ["homer"]
    HTTP_PORT = 7888
    SIP_DIGEST_REALM = "example.com"
    HTTP_UNIX = "/tmp/.homer-sock"

Logging
=======

The logging level is set to INFO by default. To also view DEBUG logs add the
following to `src/metaswitch/crest/local_settings.py`.

    LOG_LEVEL = logging.DEBUG


Cassandra
=========

Crest is backed by a Cassandra database, which is automatically installed and configured
by the Debian package. For development it is useful to run a local Cassandra database.
Alternatively, just point Crest at an existing Cassandra database, by modifying the
`CASS_HOST` parameter `local_settings.py`.

Once you have a database running, you will need to make sure the correct keyspaces exist.
These are set up by the cassandra-schemas scripts - to run these manually the commands are:

For Homestead-prov:

    echo "CREATE KEYSPACE homestead_provisioning WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
          USE homestead_provisioning;
          CREATE TABLE implicit_registration_sets (id uuid PRIMARY KEY, dummy text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
          CREATE TABLE service_profiles (id uuid PRIMARY KEY, irs text, initialfiltercriteria text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
          CREATE TABLE public (public_id text PRIMARY KEY, publicidentity text, service_profile text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
          CREATE TABLE private (private_id text PRIMARY KEY, digest_ha1 text, realm text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | cqlsh 

If you haven't already set up Homestead, you will also need to install the `homestead_cache` keyspace:

    echo "CREATE KEYSPACE homestead_cache WITH REPLICATION =  {'class': 'SimpleStrategy', 'replication_factor': 2};
          USE homestead_cache;
          CREATE TABLE impi (private_id text PRIMARY KEY, digest_ha1 text, digest_realm text, digest_qop text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
          CREATE TABLE impu (public_id text PRIMARY KEY, ims_subscription_xml text, is_registered Boolean, primary_ccf text, secondary_ccf text, primary_ecf text, secondary_ecf text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;
          CREATE TABLE impi_mapping (private_id text PRIMARY KEY, unused text) WITH COMPACT STORAGE AND read_repair_chance = 1.0; | cqlsh

For Homer:

    echo "CREATE KEYSPACE homer WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 2};
          USE homer;
          CREATE TABLE simservs (user text PRIMARY KEY, value text) WITH COMPACT STORAGE AND read_repair_chance = 1.0;" | cqlsh

The easiest way to examine what is in the database is to use cqlsh, e.g.

    cqlsh 
    use <keyspace>;
    SELECT * FROM <table>;

For details of the CQL syntax, see [the CQL documentation](http://cassandra.apache.org/doc/cql3/CQL.html).

Running the server
==================

To run the server as part of development use:

    make run

Running the tests
=================

Crest has unit tests, located at `src/metaswitch/crest/test` in parallel to the packages
being tested, e.g., the tests for `src/metaswitch/crest/api` are in `src/metaswitch/crest/test/api`

Run the tests using:

    make test

View the current UT coverage using:

    make coverage

You should aim for 100% coverage on newly-written code. At the very
least, you shouldn't reduce the coverage level when adding new code.

Bulk provisioning
=================

For testing, you may need to bulk-provision numbers. Instructions for doing this
can be found [here](Bulk-Provisioning Numbers.md).

Packaging
=========

Crest (and its derivatives) are packaged as Debian packages. These bundle up the Crest
code into a Python egg as well as including the other Python dependencies as eggs. To see
the list of dependencies, see buildout.cfg.

The files required for Debian packaging are in the Debian directory, prefixed with the component
name, i.e. the installation script for Homer is at `debian/homer.postinst`.

At the root of the Crest project are a number of configuration files that are copied into
the Debian packages, again following the prefix.path pattern. Of particular note are the
`prefix.local_settings/local_settings.py` files. These contains the overriding config
that transforms a generic Crest server into a specific component. For example, for Homer,
the HTTP port is set to 7888 here.

Debian packages are generated by:

    make deb

Running `make deb` will create Debian packages in `~/www/repo/binary`

Files
=====

* `src/` contains the source code for Crest
* `build-infra/` and `modules/` contain submodules, described above.
* `docs/` contains this documentation.
* `debian/` and `*.root/`, as well as the repository root, contain files
  used for building the install package.
* The remaining directories are mostly related to Python packaging.

