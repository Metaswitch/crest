# @file settings.py
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

import os

"""
This file contains default settings for Homer.  To override a setting
locally, create a file local_settings.py in this directory and add the override
setting to that.
"""

def ensure_dir_exists(d):
    """
    Creates the directory d if it doesn't exist.  Raises an exception iff the
    directory can't be created and didn't already exist.
    """
    try:
        os.makedirs(d)
    except Exception:
        pass
    if not os.path.isdir(d):
        raise RuntimeError("Failed to create dir %s" % d)


# Route configuration, which Handlers to install. Currently support "homer" and "homestead"
# By default, include both - but for production should restrict to one or the other
INSTALLED_HANDLERS = ["homer", "homestead"]

# Calculate useful directories relative to the project.
_MY_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.abspath(os.path.join(_MY_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
CERTS_DIR = os.path.join(PROJECT_DIR, "certificates")

# Logging - log files will have names homer-XXX.log, where XXX is the task id
LOG_FILE_PREFIX = "homer"
LOG_FILE_MAX_BYTES = 10000000
LOG_BACKUP_COUNT = 10
PID_FILE = os.path.join(PROJECT_DIR, "server.pid")

# Ports.
HTTP_PORT = 8888

# We use this key to encrypt sensitive fields in the database that we can't
# avoid storing.  In general, we'd like to store passwords as bcrypt hashes
# but we can only do that if the password is sent to us by the user in the 
# clear.  Encrypting the password in the DB at least mitigates DB injection
# attacks and prevents accidental exposure to staff.
PASSWORD_ENCRYPTION_KEY = '2lB6HWYd1cvuGbAdey9cFL5bSWDzxHOsYyPLYOxV3Bs'

# Tornado cookie encryption key.  Tornado instances that share this key will 
# all trust each other's cookies.
COOKIE_SECRET = '4<HqJaa5wi]EjSEq4^vpm#oCWp#$HJ#>exzD7bAa'

# SIP parameters
SIP_DIGEST_REALM = 'cw-ngv.com'

# Cassandra configuration
CASS_HOST = "localhost"
CASS_PORT = 9160
CASS_KEYSPACE = "default"

# HSS configuration (by default, syncronization with the HSS is disabled)
HSS_ENABLED = False
HSS_IP = "0.0.0.0"
HSS_PORT = 3868
# Debian install will pick this up from /etc/clearwater/config
SPROUT_HOSTNAME = "sprout.%s" % SIP_DIGEST_REALM
SPROUT_PORT = 5058

# To avoid deploying with debug turned on, these settings should only ever be 
# changed by creating a local_settings.py file in this directory.
CYCLONE_DEBUG = False  # Make cyclone emit debug messages to the browser etc.

# Include any locally-defined settings.
_local_settings_file = os.path.join(_MY_DIR, "local_settings.py")
if os.path.exists(_local_settings_file):
    execfile(_local_settings_file)

# Must do this after we've loaded the local settings, in case the paths change
ensure_dir_exists(LOGS_DIR)
ensure_dir_exists(DATA_DIR)
