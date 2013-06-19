# @file __init__.py
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


from cyclone.web import RequestHandler
import cyclone.web

from metaswitch.crest.api import PATH_PREFIX
from metaswitch.crest.api import settings
from metaswitch.crest.api.homestead.credentials import CredentialsHandler
from metaswitch.crest.api.homestead.filtercriteria import FilterCriteriaHandler
from metaswitch.crest.api.homestead.hss import gateway

# TODO More precise regexes
PRIVATE_ID = r'[^/]+'
PUBLIC_ID = r'[^/]+'

# Routes for application. Each route consists of:
# - The actual route regex, with capture groups for parameters that will be passed to the the Handler
# - The Handler to process the request. If no validation is required, use the PassthroughHandler.
#   To validate requests, subclass PassthroughHandler and validate before passing onto PassthroughHandler
# - Cassandra information. This hash contains the information required by PassthroughHandler to store
#   the data in the underlying database. Namely:
#     - table: the table to store the values in
#     - column: name of the column to store against in Cassandra. The value stored is the request body
ROUTES = [
    # Credentials
    # /credentials/<private ID>/<public ID>/(digest|aka)
    (PATH_PREFIX + r'credentials/(' + PRIVATE_ID + r')/(' + PUBLIC_ID + r')/digest/?$',
     CredentialsHandler,
     {"table": "sip_digests", "column": "digest"}),

    # Credentials for clients which need a SIP Digest but legitimately
    # do not have a public ID. This API is for such clients only; most
    # clients should use the credentials API instead. Only GET is
    # supported.
    # /privatecredentials/<private ID>/digest
    (PATH_PREFIX + r'privatecredentials/(' + PRIVATE_ID + r')/digest/?$',
     CredentialsHandler,
     {"table": "sip_digests", "column": "digest"}),

    # IFC
    # /filtercriteria/<public ID>
    (PATH_PREFIX + r'filtercriteria/(' + PUBLIC_ID + r')/?$',
     FilterCriteriaHandler,
     {"table": "filter_criteria", "column": "value"}),
]

# Initial Cassandra table creation. Whenever you add a route to the URLS above, add
# a CQL CREATE statement below
CREATE_SIP_DIGESTS = "CREATE TABLE sip_digests (private_id text, digest text, PRIMARY KEY (private_id));"
CREATE_IFCS = "CREATE TABLE filter_criteria (public_id text, value text, PRIMARY KEY (public_id));"
CREATE_STATEMENTS = [CREATE_SIP_DIGESTS, CREATE_IFCS]

# Module initialization
def initialize(application):
    if settings.HSS_IP not in ["", "0.0.0.0"]:
        application.hss_gateway = gateway.HSSGateway()
