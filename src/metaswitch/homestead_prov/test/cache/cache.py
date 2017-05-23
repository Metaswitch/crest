#!/usr/bin/python

# @file cache.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import mock
import unittest

from twisted.internet import defer
from telephus.cassandra.ttypes import Column, Deletion, NotFoundException

from metaswitch.homestead_prov import authtypes
from metaswitch.homestead_prov.cache.cache import Cache
from metaswitch.homestead_prov.auth_vectors import DigestAuthVector
from metaswitch.homestead_prov.cache.db import CacheModel
from metaswitch.crest.test.matchers import DictContaining, ListContaining

def MockColumn(name, val):
    m = mock.MagicMock()
    m.column.name = name
    m.column.value = val
    return m

class Result(object):
    def __init__(self, deferred):
        self.callback = mock.MagicMock()
        self.errback = mock.MagicMock()
        deferred.addCallback(self.callback)
        deferred.addErrback(self.errback)

    def value(self):
        if self.errback.called:
            raise self.errback.call_args[0][0]
        return self.callback.call_args[0][0]

class TestCache(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)

        patcher = mock.patch("metaswitch.homestead_prov.cassandra.CassandraClient")
        self.CassandraClient = patcher.start()
        self.addCleanup(patcher.stop)

        self.cass_client = mock.MagicMock()
        self.CassandraClient.return_value = self.cass_client

        CacheModel.start_connection()
        self.cache = Cache()

        # Dummy TTL and timestamp used for cache puts.
        self.ttl = 123
        self.timestamp = 1234

    def test_put_av_digest(self):
        """Test a digest can be put into the cache"""

        auth = DigestAuthVector("ha1_test", "realm", "qop")

        self.cass_client.batch_insert.return_value = batch_insert = defer.Deferred()
        res = Result(self.cache.put_av("priv", auth, self.timestamp, ttl=self.ttl))
        self.cass_client.batch_insert.assert_called_once_with(
            key="priv",
            column_family="impi",
            mapping=DictContaining({"digest_ha1": "ha1_test",
                                    "digest_realm": "realm",
                                    "digest_qop": "qop"}),
            ttl=self.ttl,
            timestamp=self.timestamp)
        batch_insert.callback(None)
        self.assertEquals(res.value(), None)

    def test_put_associated_public_id(self):
        """Test a public ID associated with the private ID can be put into the
        cache"""

        self.cass_client.batch_insert.return_value = batch_insert = defer.Deferred()
        res = Result(self.cache.put_associated_public_id("priv",
                                                         "kermit",
                                                         self.timestamp,
                                                         ttl=self.ttl))
        self.cass_client.batch_insert.assert_called_once_with(
                                             key="priv",
                                             column_family="impi",
                                             mapping=DictContaining({"public_id_kermit": ""}),
                                             ttl=self.ttl,
                                             timestamp=self.timestamp)
        batch_insert.callback(None)
        self.assertEquals(res.value(), None)

    def test_get_associated_public_ids(self):
        """Test retrieval of the public ids associated with the specified private ID"""
        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_associated_public_ids("priv"))
        self.cass_client.get_slice.assert_called_once_with(
                                                 key="priv",
                                                 column_family="impi",
                                                 names=None)
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("public_id_sip:foo@bar.com", ""),
                            MockColumn("public_id_sip:bar@baz.com", ""),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value(), ["sip:foo@bar.com", "sip:bar@baz.com"])

    def test_get_associated_public_ids_none(self):
        """Test retrieval of the public ids associated with the specified private ID"""
        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_associated_public_ids("priv"))
        self.cass_client.get_slice.assert_called_once_with(
                                                 key="priv",
                                                 column_family="impi",
                                                 names=None)
        get_slice.errback(NotFoundException())
        self.assertEquals(res.value(), [])

    def test_put_ims_subscription(self):
        """Test an IMS subscription can be put into the cache"""
        self.cass_client.batch_insert.return_value = batch_insert = defer.Deferred()
        res = Result(self.cache.put_ims_subscription("pub",
                                                     "xml",
                                                     self.timestamp,
                                                     ttl=self.ttl))
        self.cass_client.batch_insert.assert_called_once_with(
                                        key="pub",
                                        column_family="impu",
                                        mapping=DictContaining({"ims_subscription_xml": "xml", "primary_ccf": "ccf"}),
                                        ttl=self.ttl,
                                        timestamp=self.timestamp)
        batch_insert.callback(None)
        self.assertEquals(res.value(), None)

    def test_put_multi_ims_subscription(self):
        """Test multiple IMS subscriptions can be put into the cache"""
        self.cass_client.batch_mutate.return_value = batch_mutate = defer.Deferred()
        res = Result(self.cache.put_multi_ims_subscription(["pub1", "pub2"],
                                                           "xml",
                                                           ttl=self.ttl,
                                                           timestamp=self.timestamp))
        row = {"impu": [Column("ims_subscription_xml", "xml", self.timestamp, self.ttl),
                        Column("_exists", "", self.timestamp, self.ttl)]}
        self.cass_client.batch_mutate.assert_called_once_with({"pub1": row, "pub2": row})
        batch_mutate.callback(None)
        self.assertEquals(res.value(), None)

    def test_get_ims_subscription(self):
        """Test an IMS subscription can be fetched from the cache"""

        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_ims_subscription("pub"))

        self.cass_client.get_slice.assert_called_once_with(
                                                 key="pub",
                                                 column_family="impu",
                                                 names=ListContaining(["ims_subscription_xml"]))
        get_slice.callback([MockColumn("ims_subscription_xml", "xml"),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value(), "xml")

    def test_get_digest_no_pub_id_supp(self):
        """Test a digest can be got from the cache when no public ID is
        supplied"""

        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_av("priv"))

        self.cass_client.get_slice.assert_called_once_with(
                                                 key="priv",
                                                 column_family="impi",
                                                 names=ListContaining(["digest_ha1"]))
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value().ha1, "digest")

    def test_get_digest_no_pub_id_assoc(self):
        """Test that is you specify a required public ID when getting a digest,
        that nothing is returned if that ID is not associated with the private
        ID."""

        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_av("priv", "miss_piggy"))

        self.cass_client.get_slice.assert_called_once_with(
                                   key="priv",
                                   column_family="impi",
                                   names=ListContaining(["digest_ha1", "public_id_miss_piggy"]))
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("public_id_kermit", None),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value(), None)

    def test_get_digest_right_pub_id(self):
        """Test that is you specify a required public ID when getting a digest,
        that the digest IS returned if that ID IS associated with the private
        ID."""

        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_av("priv", "miss_piggy"))

        self.cass_client.get_slice.assert_called_once_with(
                                   key="priv",
                                   column_family="impi",
                                   names=ListContaining(["digest_ha1", "public_id_miss_piggy"]))
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("public_id_miss_piggy", None),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value().ha1, "digest")

    def test_get_digest_unknown(self):

        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_av("priv", "miss_piggy", authtypes.UNKNOWN))

        self.cass_client.get_slice.assert_called_once_with(
                                   key="priv",
                                   column_family="impi",
                                   names=ListContaining(["digest_ha1", "public_id_miss_piggy"]))
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("public_id_miss_piggy", None),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value(), None)

    def test_get_digest_sip(self):
        self.cass_client.get_slice.return_value = get_slice = defer.Deferred()
        res = Result(self.cache.get_av("priv", "miss_piggy", authtypes.SIP_DIGEST))

        self.cass_client.get_slice.assert_called_once_with(
                                   key="priv",
                                   column_family="impi",
                                   names=ListContaining(["digest_ha1", "public_id_miss_piggy"]))
        get_slice.callback([MockColumn("digest_ha1", "digest"),
                            MockColumn("public_id_miss_piggy", None),
                            MockColumn("_exists", "")])
        self.assertEquals(res.value().ha1, "digest")

    def test_delete_multi_private_ids(self):
        """Test deleting multiple private IDs from the cache"""
        self.cass_client.batch_mutate.return_value = batch_mutate = defer.Deferred()
        res = Result(self.cache.delete_multi_private_ids(["priv1", "priv2"], self.timestamp))
        row = {"impi": [Deletion(self.timestamp)]}
        self.cass_client.batch_mutate.assert_called_once_with({"priv1": row, "priv2": row})
        batch_mutate.callback(None)
        self.assertEquals(res.value(), None)

    def test_delete_multi_public_ids(self):
        """Test deleting multiple public IDs from the cache"""
        self.cass_client.batch_mutate.return_value = batch_mutate = defer.Deferred()
        res = Result(self.cache.delete_multi_public_ids(["pub1", "pub2"], self.timestamp))
        row = {"impu": [Deletion(self.timestamp)]}
        self.cass_client.batch_mutate.assert_called_once_with({"pub1": row, "pub2": row})
        batch_mutate.callback(None)
        self.assertEquals(res.value(), None)
