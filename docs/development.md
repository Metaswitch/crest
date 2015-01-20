Crest - Development Guide
===========

These instructions have been tested on Ubuntu 12.04, using Python version 2.7.3.

Get the code
============

    git clone --recursive git@github.com:Metaswitch/crest.git

This accesses the repository over SSH on Github, and will not work unless you have a Github account and registered SSH key. If you do not have both of these, you will need to configure Git to read over HTTPS instead:

    git config --global url."https://github.com/".insteadOf git@github.com:
    git clone --recursive git@github.com:Metaswitch/crest.git

The code consists of the `crest` repository and its submodules as
defined in `.gitmodules`:

* `python-common`, which appears at `modules/common/`, contains Python utility
  code shared between the Python components of Clearwater.
* `clearwater-build-infra`, which appears at `build-infra/`, contains
  support for building Debian packages which is shared between all
  components of Clearwater.
* `pure-sasl`, which appears at `modules/pure-sasl/`, a Python SASL implemention
* `sdp`, which appears at `modules/sdp/`, a Python diameter stack
* `telephus`, which appears at `modules/telephus/`, a Twisted Cassandra API

Pre-requisites
==============
1. Pip and virtualenv

    ```
    sudo apt-get install python-pip python-dev python-virtualenv build-essential
    ```

2. Lib-curl

    ```
    sudo apt-get install libcurl4-openssl-dev
    ```

3. Building debian packages

    ```
    sudo apt-get install debhelper devscripts
    ```

4. XML development libraries

    ```
    sudo apt-get install libxml2-dev libxslt-dev
    ```

5. Python static analysis checker

   ```
   sudo pip install flake8 mccabe pep8-naming
   ```

6. ZMQ libraries

   ```
   sudo apt-get install python-zmq libzmq3-dev
   ```

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

For a homestead node, you'll probably need at least the following in
`local_settings.py` (replacing `example.com` with the correct domain).

    LOG_FILE_PREFIX = "homestead-prov"
    PROCESS_NAME = "homestead-prov"
    INSTALLED_HANDLERS = ["homestead"]
    HTTP_PORT = 8888
    HSS_ENABLED = False
    SIP_DIGEST_REALM = example.com

For a homer node, you'll probably need the following instead.

    LOG_FILE_PREFIX = "homer"
    PROCESS_NAME = "homer"
    INSTALLED_HANDLERS = ["homer"]
    HTTP_PORT = 7888
    SIP_DIGEST_REALM = example.com

Logging
=======

The logging level is set to INFO by default. To also view DEBUG logs add the
following to `src/metaswitch/crest/local_settings.py`.

    LOG_LEVEL = logging.DEBUG


Cassandra
=========

Crest is backed by a Cassandra database, which is automatically installed and configured
by the debian package. For development it is useful to run a local Cassandra database.
Alternatively, just point Crest at an existing Cassandra database, by modifying the
`CASS_HOST` parameter `local_settings.py`.

Once you have a database running, you will need to make sure the correct keyspace exists.
This is setup by the `debian/<component>.postinst` scripts, so make sure you run the relevant
command before developing - e.g. for homer:

    echo "create KEYSPACE homer with strategy_class = 'SimpleStrategy' AND strategy_options:replication_factor = 2;" | cqlsh -3 localhost

Next, to actually create the database run the `create_db.py` script:

    PYTHONPATH=src bin/python src/metaswitch/crest/tools/create_db.py

The easiest way to examine what is in the database is to use cqlsh, e.g.

    cqlsh -3
    use homestead_cache;
    SELECT * FROM impi;

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

Crest (and its derivatives) are packaged as debian packages. These bundle up the Crest
code into a Python egg as well as including the other Python dependencies as eggs. To see
the list of dependencies, see buildout.cfg.

The files required for debian packaging are in the debian directory, prefixed with the component
name, i.e. the installation script for homer is at `debian/homer.postinst`.

At the root of the Crest project are a number of configuration files that are copied into
the debian packages, again following the prefix.path pattern. Of particular note are the
`prefix.local_settings/local_settings.py` files. These contains the overriding config
that transforms a generic Crest server into a specific component. For example, for Homer,
the HTTP port is set to 7888 here.

Debian packages are generated by:

    make deb

Running `make deb` will create debian packages in `~/www/repo/binary`

Files
=====

* `src/` contains the source code for Crest
* `build-infra/` and `modules/` contain submodules, described above.
* `docs/` contains this documentation.
* `debian/` and `*.root/`, as well as the repository root, contain files
  used for building the install package.
* The remaining directories are mostly related to Python packaging.

