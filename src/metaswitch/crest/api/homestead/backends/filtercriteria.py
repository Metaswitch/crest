# @file filtercriteria.py
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
import httplib

from cyclone.web import HTTPError
from telephus.cassandra.ttypes import NotFoundException
from twisted.internet import defer

from metaswitch.common import utils
from metaswitch.crest import settings
from metaswitch.crest.api.passthrough import PassthroughHandler
from metaswitch.crest.api.homestead.hss.gateway import HSSNotFound

_log = logging.getLogger("crest.api.homestead")

class FilterCriteriaHandler(PassthroughHandler):
    """
    Handler for Initial Filter Criteria
    """
    @defer.inlineCallbacks
    def get(self, public_id):
        try:
            result = yield self.cass.get(column_family=self.table,
                                         key=public_id,
                                         column=self.column)
            ifc = result.column.value
        except NotFoundException, e:
            if not settings.HSS_ENABLED:
                # No HSS
                raise HTTPError(404)
            # IFC not in Cassandra, attempt to fetch from HSS
            try:
                # TODO For now we assume to same public to private id mapping as ellis
                private_id = utils.sip_public_id_to_private(public_id)
                ifc = yield self.application.hss_gateway.get_ifc(private_id, public_id)
            except HSSNotFound:
                raise HTTPError(404)
            # Have result from HSS, store in Cassandra
            yield self.cass.insert(column_family=self.table,
                                   key=public_id,
                                   column=self.column,
                                   value=ifc)
        self.finish(ifc)
