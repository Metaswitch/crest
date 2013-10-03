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

from ..backend import Backend
from .gateway import HSSGateway

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
        self._hss_gateway = HSSGateway()

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
                                             timestamp)
                yield self._cache.put_associated_public_id(private_id,
                                                           public_id,
                                                           timestamp)
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
                                                   timestamp)

        defer.returnValue(ims_subscription)
