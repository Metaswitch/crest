# @file handlers.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

from twisted.internet import defer
import logging

from .. import config
from metaswitch.crest import settings
from ..cassandra import CassandraModel
from telephus.cassandra.ttypes import NotFoundException

DIGEST_HA1 = "digest_ha1"
DIGEST_REALM = "digest_realm"
DIGEST_QOP = "digest_qop"
PUBLIC_ID_PREFIX = "public_id_"

_log = logging.getLogger("crest.api.homestead.cache")


class CacheModel(CassandraModel):
    cass_keyspace = config.CACHE_KEYSPACE


class IMPI(CacheModel):
    cass_table = config.IMPI_TABLE

    @defer.inlineCallbacks
    def get_av(self, public_id):
        try:
            query_columns = [DIGEST_HA1, DIGEST_REALM, DIGEST_QOP]
            if public_id:
                public_id_column = PUBLIC_ID_PREFIX+str(public_id)
                query_columns.append(public_id_column)

            columns = yield self.get_columns(query_columns)

            realm = columns.get(DIGEST_REALM, None)
            qop = columns.get(DIGEST_QOP, None)

            # It the user has supplied a public ID, they care about whether the
            # private ID can authenticate the public ID.  Only return a digest
            # if the public ID is associated with the private ID.
            if (DIGEST_HA1 in columns):
                if (public_id is None or public_id_column in columns):
                    defer.returnValue((columns[DIGEST_HA1], realm, qop))
                else:
                    _log.debug("Not returning digest for private ID %s as "
                               "public ID %s is not in columns: %s" %
                               (self.row_key, public_id, columns.keys()))

        except NotFoundException:
            pass

    @defer.inlineCallbacks
    def put_av(self, ha1, realm, qop, ttl=None, timestamp=None):
        yield self.modify_columns({DIGEST_HA1: ha1,
                                   DIGEST_REALM: realm,
                                   DIGEST_QOP: qop}, ttl=ttl, timestamp=timestamp)

    @defer.inlineCallbacks
    def put_associated_public_id(self, public_id, ttl=None, timestamp=None):
        public_id_column = PUBLIC_ID_PREFIX + public_id
        yield self.modify_columns({public_id_column: ""}, ttl=ttl, timestamp=timestamp)

    @defer.inlineCallbacks
    def get_associated_public_ids(self):
        try:
            columns = yield self.get_columns_with_prefix_stripped(PUBLIC_ID_PREFIX)
            _log.debug("Retrieved list of public IDs %s for private ID %s" %
                       (str(columns.keys()), self.row_key))
            defer.returnValue(columns.keys())
        except NotFoundException:
            _log.debug("No public IDs found for private ID %s" % self.row_key)
            defer.returnValue([])

    @classmethod
    @defer.inlineCallbacks
    def delete_multi_private_ids(cls, private_ids, timestamp=None):
        yield cls.delete_rows(private_ids, timestamp=timestamp)

IMS_SUBSCRIPTION = "ims_subscription_xml"
PRIMARY_CCF = "primary_ccf"


class IMPU(CacheModel):
    cass_table = config.IMPU_TABLE

    @defer.inlineCallbacks
    def get_ims_subscription(self):
        try:
            retval = yield self.get_column_value(IMS_SUBSCRIPTION)
            defer.returnValue(retval)

        except NotFoundException:
            pass

    @defer.inlineCallbacks
    def put_ims_subscription(self, ims_subscription, ttl=None, timestamp=None):
        yield self.modify_columns({IMS_SUBSCRIPTION: ims_subscription,
                                   PRIMARY_CCF: settings.CCF},
                                  ttl=ttl,
                                  timestamp=timestamp)

    @classmethod
    @defer.inlineCallbacks
    def put_multi_ims_subscription(cls, public_ids, ims_subscription, ttl=None, timestamp=None):
        yield cls.modify_columns_multikeys(public_ids,
                                           {IMS_SUBSCRIPTION: ims_subscription},
                                           ttl=ttl,
                                           timestamp=timestamp)

    @classmethod
    @defer.inlineCallbacks
    def delete_multi_public_ids(cls, public_ids, timestamp=None):
        yield cls.delete_rows(public_ids, timestamp=timestamp)
