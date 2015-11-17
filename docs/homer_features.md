Homer Feature List
==================

Homer is the XDMS component in Clearwater. The full specification can be found [here](http://technical.openmobilealliance.org/Technical/release_program/docs/XDM/V2_0-20090810-C/OMA-TS-XDM_Core-V2_0-20090810-C.pdf), 
however Homer only currently implements a subset of the features detailed
in the specification. Specifically, currently the following portions of the 
XCAP protocol are not supported:

* HTTP Digest Auth (s5.1.1), X-XCAP-Asserted-Identity and friends (s5.1.2), or any of the other security/authorization
* XCAP Server Capabilities (s5.3.1)
* XML Documents Directory (s5.3.2)
* Search (s5.4.1, s6.1.3 etc)
* Any Global Documents (s5.5)
* Subscriptions (s6.1.2 etc)
* Creating or replacing an element in a document [RFC4825 s7.4](http://tools.ietf.org/html/rfc4825#section-7.4)
* Deleting an element in a document [RFC4825 s7.5](http://tools.ietf.org/html/rfc4825#section-7.5)
* Fetching an element in a document [RFC4825 s7.6](http://tools.ietf.org/html/rfc4825#section-7.6)
* Creating or replacing an attribute [RFC4825 s7.7](http://tools.ietf.org/html/rfc4825#section-7.7)/[deleting (s7.8)](http://tools.ietf.org/html/rfc4825#section-7.8) / [fetching (s7.9)](http://tools.ietf.org/html/rfc4825#section-7.9)
* Fetching namespace bindings [RFC4825 s7.10](http://tools.ietf.org/html/rfc4825#section-7.10)
* Conditional requests [RFC4825 s7.11](http://tools.ietf.org/html/rfc4825#section-7.11)

Authentication
--------------

In a Clearwater deployment, a Homer node must be locked down using firewalls
such that it is only visible to other nodes, and not externally. Any client
able to send traffic to port 7888 of a Homer node may perform any operation on
any data stored in Homer, without providing any authentication; allowing
external access therefore presents a significant security risk.

Simservs document storage
-------------------------

Homer provides a [RESTful HTTP interface](homer_api.md) for storing and retrieving
simservs XML documents

XSD Schema validation
---------------------

Homer performs schema validation on all simservs documents passed to it, rejecting 
those that fail. The full specification can be found [here](http://www.etsi.org/deliver/etsi_ts/129300_129399/129364/08.00.00_60/ts_129364v080000p.pdf)

Conflict reports are not currently supported.

Bulk provisioning
-----------------

Homer supports bulk provisioning a large set of subscribers from a CSV file, via a set of command line tools.

Scalability
-----------

Being based on Crest, Homer is horizontally scalable. A cluster of Homer nodes
provides access to the same underlying Cassandra cluster, allowing the load to
be spread between nodes.

Additional document storage and validation
------------------------------------------

Additional documents can be stored in homer by providing an extra handler
definition file.  This maps an XDMS path and filename to a schema file,
cassandra table and cassandra column.  See simservs.json for a sample
handler description that describes the simservs document storage.
