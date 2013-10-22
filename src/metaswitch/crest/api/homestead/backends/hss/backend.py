# @file backend.py
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version, along with the "Special Exception" for use of
# the program along with SSL, set forth below. This program is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details. You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by
# post at Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK
#
# Special Exception
# Metaswitch Networks Ltd  grants you permission to copy, modify,
# propagate, and distribute a work formed by combining OpenSSL with The
# Software, or a work derivative of such a combination, even if such
# copying, modification, propagation, or distribution would otherwise
# violate the terms of the GPL. You must comply with the GPL in all
# respects for all of the code used other than OpenSSL.
# "OpenSSL" means OpenSSL toolkit software distributed by the OpenSSL
# Project and licensed under the OpenSSL Licenses, or a work based on such
# software and licensed under the OpenSSL Licenses.
# "OpenSSL Licenses" means the OpenSSL License and Original SSLeay License
# under which the OpenSSL Project distributes the OpenSSL toolkit software,
# as those licenses appear in the file LICENSE-OPENSSL.

import logging

from twisted.internet import defer
from xml.etree import ElementTree

from ..backend import Backend
from .gateway import HSSGateway
from metaswitch.crest import settings
from metaswitch.crest.api import utils

_log = logging.getLogger("crest.api.homestead.hss")


class HSSBackend(Backend):
    """
    A backend that gets its data from a real HSS.

    This class is responsible for querying the HSS and updating the cache with
    the returned results.  The actual communication with the HSS is handled by
    the HSSGateway class.
    """

    def __init__(self, cache):
        self._cache = cache
        self._hss_gateway = HSSGateway(HSSBackend.Callbacks(cache))

    @defer.inlineCallbacks
    def get_digest(self, private_id, public_id=None):
        if not public_id:
            # We can't query the HSS without a public ID.
            _log.error("Cannot get digest for private ID '%s' " % private_id +
                       "as no public ID has been supplied")
            defer.returnValue(None)
        else:
            digest = yield self._hss_gateway.get_digest(private_id,
                                                        public_id)
            _log.debug("Got digest %s for private ID %s from HSS" %
                       (digest, private_id))

            if digest:
                # Update the cache with the digest, and the fact that the
                # private ID can authenticate the public ID.
                timestamp = self._cache.generate_timestamp()
                yield self._cache.put_digest(private_id,
                                             digest,
                                             timestamp,
                                             ttl=settings.HSS_AUTH_CACHE_PERIOD_SECS)
                yield self._cache.put_associated_public_id(private_id,
                                                           public_id,
                                                           timestamp,
                                                           ttl=settings.HSS_ASSOC_IMPU_CACHE_PERIOD_SECS)
            defer.returnValue(digest)

    @defer.inlineCallbacks
    def get_ims_subscription(self, public_id, private_id=None):
        # Note that _get_ims_subscription_ on the gateway has the public and
        # private IDs in a different order from this method.
        ims_subscription = yield self._hss_gateway.get_ims_subscription(
                                                                    private_id,
                                                                    public_id)
        _log.debug("Got IMS subscription %s for private ID %s from HSS" %
                   (ims_subscription, private_id))

        if ims_subscription:
            timestamp = self._cache.generate_timestamp()
            yield self._cache.put_ims_subscription(public_id,
                                                   ims_subscription,
                                                   timestamp,
                                                   ttl=settings.HSS_IMS_SUB_CACHE_PERIOD_SECS)

        defer.returnValue(ims_subscription)

    class Callbacks:
        """
        Inner class to bundle up callbacks invoked by HSSGateway when the HSS sends notification
        of changes.
        """
        def __init__(self, cache):
            self._cache = cache

        def on_digest_change(self, private_id, digest):
            return self._cache.put_digest(private_id,
                                          digest,
                                          self._cache.generate_timestamp(),
                                          ttl=settings.HSS_AUTH_CACHE_PERIOD_SECS)

        @defer.inlineCallbacks
        def on_ims_subscription_change(self, ims_subscription):
            xml = ElementTree.fromstring(ims_subscription)
            # Iterate over all public IDs in the subscription, storing it against
            # each one.
            timestamp = self._cache.generate_timestamp()
            public_ids = [pi.text for pi in xml.iterfind('./ServiceProfile/PublicIdentity/Identity')]
            _log.debug("Updating IMS subscriptions for %s: %s" % (str(public_ids), ims_subscription))
            yield self._cache.put_multi_ims_subscription(public_ids,
                                                         ims_subscription,
                                                         timestamp,
                                                         ttl=settings.HSS_IMS_SUB_CACHE_PERIOD_SECS)
            _log.debug("Updated IMS subscriptions")

        @defer.inlineCallbacks
        def on_forced_expiry(self, private_ids, public_ids=None):
            # If we weren't given a list of public IDs, look them up from the private IDs.
            deferreds = []
            if not public_ids:
                # Query the public IDs associated with all public IDs.  This is quite intensive
                # but we don't expect the list of private IDs to be long.
                deferreds = [self._cache.get_associated_public_ids(id) for id in private_ids]
                results = yield defer.gatherResults(deferreds, consumeErrors=True)
                public_ids = utils.flatten(results)
                # Remove any duplicates.
                public_ids = list(set(public_ids))
                _log.debug("Retrieved public IDs %s" % str(public_ids))
            timestamp = self._cache.generate_timestamp()
            # Delete all the public and private IDs from the cache.  Note that technically we
            # needn't flush private IDs if there are still public IDs remaining.  However, it's
            # simpler (and, given this is a rare operation, not too performance-impacting) just to
            # flush these too.
            yield defer.DeferredList([self._cache.delete_multi_private_ids(private_ids, timestamp=timestamp),
                                      self._cache.delete_multi_public_ids(public_ids, timestamp=timestamp)],
                                     consumeErrors=True)

