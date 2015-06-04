Homestead-Prov Feature List
======================

Homestead-prov is a provisioning interface to [Homestead](https://github.com/Metaswitch/homestead). It provides a [RESTful HTTP interface](homestead_prov_api.md) for creating/deleting/querying subscribers. It should only be used when Homestead holds the master copy of the subscriber data (so not if the deployment uses a real HSS). 

Authentication
--------------

In a Clearwater deployment, a Homestead-prov node must be locked down using firewalls such that it is only visible to other nodes (typically just Ellis), and not externally (except to known clients that are allowed to access the Homestead-prov API). 

Any client able to send traffic to port 8889 of a Homestead-prov node may create/delete/query a subscriber, without providing any authentication; allowing external access therefore presents a significant security risk.

Bulk provisioning
-----------------

Homestead-prov supports bulk provisioning a large set of subscribers from a CSV file, via a set of command line tools (described [here](https://github.com/Metaswitch/crest/blob/dev/docs/Bulk-Provisioning%20Numbers.md)).

Scalability
-----------

Being based on Crest, Homestead-prov is horizontally scalable. A cluster of Homestead-prov nodes
provides access to the same underlying Cassandra cluster, allowing the load to
be spread between nodes.
