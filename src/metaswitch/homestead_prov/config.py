# @file config.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

# Keyspaces
# If you change either of these, check whether changes to backup scripts are
# also required
CACHE_KEYSPACE = "homestead_cache"
PROVISIONING_KEYSPACE = "homestead_provisioning"

# Cache tables.
IMPI_TABLE = "impi"
IMPU_TABLE = "impu"

# Provisioning tables.
PRIVATE_TABLE = "private"
IRS_TABLE = "implicit_registration_sets"
SP_TABLE = "service_profiles"
PUBLIC_TABLE = "public"
