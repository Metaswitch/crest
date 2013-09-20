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

from metaswitch.crest.api import settings
from metaswitch.crest.api.homestead.cache.handlers import DigestHandler, IMSSubscriptionHandler
from metaswitch.crest.api.homestead.cache.cache import Cache
from metaswitch.crest.api.homestead import config
from metaswitch.crest.api.homestead.backends.hss.gateway import HSSBackend

# TODO More precise regexes
PRIVATE_ID = r'[^/]+'
PUBLIC_ID = r'[^/]+'

# Routes for application. Each route consists of:
# - The actual route regex, with capture groups for parameters that will be
# passed to the the Handler.
# - The Handler to process the request.
ROUTES = [
    # IMPI Digest: the API for getting/updating the digest of a private ID. Can
    # optionally validate whether a public ID is associated.
    #
    # /impi/<private ID>/digest?public_id=xxx
    (r'/impi/([^/]+)/digest/?',  DigestHandler),

    # IMPU: the read-only API for accessing the XMLSubscription associated with
    # a particular public ID.
    #
    # /impu/<public ID>?private_id=xxx
    (r'/impu/([^/]+)/?',  IMSSubscriptionHandler),
]

#
# Initial Cassandra table creation.
#

# Tables used by the cache.
CREATE_IMPI = (
    "CREATE TABLE "+config.IMPI_TABLE+" ("
        "private_id text PRIMARY KEY, "
        "digest text"
    ") WITH read_repair_chance = 1.0;"
)

CREATE_IMPU = (
    "CREATE TABLE "+config.IMPU_TABLE+" ("
        "public_id text PRIMARY KEY, "
        "IMSSubscription text"
    ") WITH read_repair_chance = 1.0;"
)

# Tables used by provisioning.
CREATE_PRIVATE = (
    "CREATE TABLE "+config.PRIVATE_TABLE+" ("
        "private_id text PRIMARY KEY, "
        "digest_ha1 text"
    ") WITH read_repair_chance = 1.0;"
)

CREATE_IRS = (
    "CREATE TABLE "+config.IRS_TABLE+" ("
        "id uuid PRIMARY KEY"
    ") WITH read_repair_chance = 1.0;"
)

CREATE_SP = (
    "CREATE TABLE "+config.SP_TABLE+" ("
        "id uuid PRIMARY KEY, "
        "irs uuid, "
        "initialfiltercriteria_xml text"
    ") WITH read_repair_chance = 1.0;"
)

CREATE_PUBLIC = (
    "CREATE TABLE "+config.PUBLIC_TABLE+" ("
        "public_id text PRIMARY KEY, "
        "publicidentity_xml text, "
        "service_profile uuid"
    ") WITH read_repair_chance = 1.0;"
)

CREATE_STATEMENTS = [CREATE_IMPI, CREATE_IMPU]

# Module initialization
def initialize(application):
    application.cache = Cache()
    ProvisioingModel.register_cache(application.cache)

    if settings.HSS_ENABLED:
        application.backend = HSSBackend(application.cache)
    else:
        application.backend = None
