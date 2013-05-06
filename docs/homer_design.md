High Level Design - Homer
========================

This document explains the high-level design of Homer, an XDMS
server built on top of Crest. It is assumed that the reader is
familiar with the design of Crest, described here:

* [Crest Design](design.md)

Overview
========

Homer is a simple extension of the vanilla Crest server.
The only extra functionality that is provided is XSD validation for
simservs documents, at the point at which they are PUT into the database.

Simservs validation
==================

The XSD validator is implemented as a python decorator, such that a route
method can be decorated with it in order to protect PUT requests from getting
through if they fail the validation. E.g.

    @xsd.validate(SCHEMA_PATH)
    def put(self, *args):
        PassthroughHandler.put(self, *args)

XSD functional tests
====================

As the XSD validation schema are complicated, in addition to unit tests
Homer has functional tests which allow asserting of whether certain
documents pass of fail validation. See `src/metaswitch/crest/test/api/homer/simservs.py`
and the xml documents in `src/metaswitch/crest/test/api/homer/test_xml`
