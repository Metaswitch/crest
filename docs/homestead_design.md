High Level Design - Homestead
========================

This document explains the high-level design of Homestead, an HSS
cache server built on top of Crest. It is assumed that the reader is
familiar with the design of Crest, described here:

* [Crest Design](design.md)

Overview
========

Homestead is a simple extension of the vanilla Crest server. It stores
the digest authentication as well as the iFCs (initial filter criteria)
for each subscriber in a Clearwater system.

Real HSS-caching (currently incomplete implementation)
========================================================

The long term design for Homestead is that is will act as cache to
a real HSS server, rather than being the master store itself.

Currently this functionality is only partially implemented, in that
if Homestead does not have a record for a subscriber in its database,
it will query the HSS and attempt to import it.

In the future, Homestead will support full two-way synchronization with the HSS.

To enable HSS caching, make the following changes in the `local_settings.py` file:

* Set `HSS_ENABLED` to True
* Set `HSS_IP` and `HSS_PORT` to the values of the HSS to cache
