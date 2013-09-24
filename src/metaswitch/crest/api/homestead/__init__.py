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

import collections

from .. import settings

from .cache.cache import Cache
from .backends.hss import HSSBackend
from .backends.provisioning import ProvisioningBackend

from .cache.handlers import DigestHandler, IMSSubscriptionHandler
from .provisioning.handlers.private import PrivateHandler, PrivateAllIrsHandler, PrivateOneIrsHandler, PrivateAllPublicIdsHandler
from .provisioning.handlers.irs import AllIRSHandler, IRSHandler, IRSAllPublicIDsHandler, IRSAllPrivateIDsHandler, IRSPrivateIDHandler
from .provisioning.handlers.service_profile import AllServiceProfilesHandler, ServiceProfileHandler, SPAllPublicIDsHandler, SPPublicIDHandler, SPFilterCriteriaHandler
from .provisioning.handlers.public import PublicIDServiceProfileHandler, PublicIDIRSHandler, PublicIDPrivateIDHandler

from .cache.db import IMPI, IMPU, CacheModel
from .provisioning.models.private_id import PrivateID
from .provisioning.models.irs import IRS
from .provisioning.models.service_profile import ServiceProfile
from .provisioning.models.public_id import PublicID
from .provisioning.models.db import ProvisioningModel

# Regex that matches a uuid.
HEX = '[a-fA-F0-9]'
UUID = '(%s{8}-%s{4}-%s{4}-%s{4}-%s{12})' % (HEX, HEX, HEX, HEX, HEX)

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

    # Private ID provisioning.
    (r'/private/([^/]+)/?', PrivateHandler),
    (r'/private/([^/]+)/associated_implicit_registration_sets/?', PrivateAllIrsHandler),
    (r'/private/([^/]+)/associated_implicit_registration_sets/([^/])/?', PrivateOneIrsHandler),
    (r'/private/([^/]+)/associated_public_ids/?', PrivateAllPublicIdsHandler),

    # Implicit Registration Set provisioning.
    (r'/irs/?', AllIRSHandler),
    (r'/irs/'+UUID+r'/?', IRSHandler),
    (r'/irs/'+UUID+r'/public_ids/?', IRSAllPublicIDsHandler),
    (r'/irs/'+UUID+r'/private_ids/?', IRSAllPrivateIDsHandler),
    (r'/irs/'+UUID+r'/private_ids/?', IRSPrivateIDHandler),

    # Service profile provisionng.
    #
    # In the class naming scheme, "all" refers to all objects in the parent
    # container (all service profiles in an IRS, or all public IDs in a
    # profile).
    (r'/irs/'+UUID+r'/service_profiles/?', AllServiceProfilesHandler),
    (r'/irs/'+UUID+r'/service_profiles/'+UUID+'/?', ServiceProfileHandler),
    (r'/irs/'+UUID+r'/service_profiles/'+UUID+'/public_ids?', SPAllPublicIDsHandler),
    (r'/irs/'+UUID+r'/service_profiles/'+UUID+'/public_ids/([^/]+)?', SPPublicIDHandler),
    (r'/irs/'+UUID+r'/service_profiles/'+UUID+'/filter_criteria/?', SPFilterCriteriaHandler),

    # Read-only privte ID interface.
    (r'/public/([^/]+)/service_profile/?', PublicIDServiceProfileHandler),
    (r'/public/([^/]+)/irs/?', PublicIDIRSHandler),
    (r'/public/([^/]+)/service_profile/?', PublicIDPrivateIDHandler),
]

# List of all the tables used by homestead.
TABLES = [IMPI, IMPU, PrivateID, IRS, ServiceProfile, PublicID]

# CREATE_STATEMENTS is a dictionary that maps keyspaces to a list of tables in
# that keyspace. Generate this now.
CREATE_STATEMENTS = collections.defaultdict(list)
for table in TABLES:
    CREATE_STATEMENTS[table.cass_keyspace].append(table.cass_create_statement)


def initialize(application):
    """Module initialization"""

    # Create a cache and register it with the provisioning models (so they keep
    # the denormalized tables in sync with the normalized ones).
    application.cache = Cache()
    ProvisioningModel.register_cache(application.cache)

    if settings.HSS_ENABLED:
        application.backend = HSSBackend(application.cache)
    else:
        application.backend = ProvisioningBackend(application.cache)

    # Connect to the cache and provisioning databases.
    ProvisioningModel.start_connection()
    CacheModel.start_connection()
