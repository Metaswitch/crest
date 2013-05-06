High Level Design
=================

This document explains the high-level design of Crest, a RESTful HTTP
CRUD server powered by a distributed Cassandra database.
It gives an overview of the major components and interfaces, and
provides pointers into the code. It is intended for people who wish
to modify, fix, or extend Crest.

The Homer and Homestead components are built on top of Crest. The design
of these are discussed in the following documents, which build on the
information described here.

* [Homer Design](homer_design.md)
* [Homestead Design](homestead_design.md)

Requirement
===========

Crest is used in Homer and Homestead, two components which act as
distributed databases in a Clearwater system. Homer is an XDMS server,
which stores the call services for subscribers, while Homestead is
a HSS cache, storing authentication and iFCs.

Both of these use cases necessitate quick read performance, but can
sacrifice write performance, as the bulk of the load on the database 
will be from reads.

Overview
========

The web framework Crest is built on is [Cyclone](http://cyclone.io/),
which is in turn built on top of [Twisted](http://twistedmatrix.com/trac/).

This allows easy configuration of routes (in Cyclone) while giving the
power of using the asynchronous nature of Twisted to handle concurrent
requests.

When a request comes into the server it is matched against a set of
routes (regular expressions), and in the case of a match, the request
is dispatched to a Handler.

A Handler is a class which deals with the request, extracting and parsing
relevant information and setting or retrieving data from the database.
Handlers use the [Telephus](https://github.com/driftx/Telephus) library
to talk to the Cassandra database.

Crest takes advantage of Twisted's @defer.inlineCallbacks feature
to make asynchronous code read as if it were synchronous, e.g.

    @defer.inlineCallbacks
    def put(self, row):
        yield self.cass.insert(column_family=self.table, key=row, column=self.column, value=self.request.body)
        self.finish({})

It is crucial you understand this powerful Twisted feature before working
with Crest. The [Twisted documentation](http://twistedmatrix.com/documents/current/core/howto/defer.html)
is a good place to start.

Crest core
==========

The main entry point to a Crest application is `src/metaswitch/ellis/main.py`.

When loaded this will start a Cyclone application, and look for ROUTES to serve
in `src/metaswitch/crest/api/__init__.py`. The ROUTES array contains tuples
that define what the Crest application will serve, and how it will store this data
in the Cassandra backend. For example, the following will serve a user at `/users/<user_id>`,
storing data in the "users" table in Cassandra:

    ROUTES = [
        (r'/users/([^/]+)/?$',
         PassthroughHandler,
         {"table": "users", "column": "value"}),
    ]

The PassthroughHandler is a simple Handler which takes what is passed to it
or requested from it and sends it to/from the database without performing any
validation. It provide the following REST verbs: GET, PUT and DELETE. See
`src/metaswitch/crest/api/passthrough.py` for details.

More complex Handlers will normally want to sub-class PassThroughHandler.

API Modules
===========

To provide flexibility, Crest has the concept of *installed Handlers*. These
are modules which are added into the `api` directory to provide additional
ROUTES and associated Handlers. It is through this mechanism that a vanilla
Crest server is made into a Homer or Homestead server. For example, the
ROUTES for Homestead are defined in `src/metaswitch/crest/api/homestead/__init__.py`

Which Handlers are installed at runtime is defined by the INSTALLED_HANDLERS
parameter in `settings.py`. When Homer and Homestead are packaged into debian
packages, this setting is configured in their respective `local_settings.py` file.

Twisted basics
==============

Unit testing code involving yields and inlineCallbacks is a little bit subtle,
as you need to mock out the Deferred object that is yielded. For an annotated example
see the following tests:

    tests/api/passthrough.py:test_get_mainline()
    tests/api/passthrough.py:test_get_not_found()

