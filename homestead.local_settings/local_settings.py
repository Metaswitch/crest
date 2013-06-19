# @file local_settings.py
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

LOGS_DIR = "/var/log/homestead"
PID_FILE = "/var/run/homestead.pid"
LOG_FILE_PREFIX = "homestead"
CASS_KEYSPACE = "homestead"
INSTALLED_HANDLERS = ["homestead"]
HTTP_PORT = 8888

# Debian install will pick this up from /etc/clearwater/config 
CASS_HOST = "localhost"

# HSS configuration (by default, synchronization with the HSS is disabled)
# Debian install will pick this up from /etc/clearwater/config 
HSS_IP = "0.0.0.0"
HSS_PORT = 3868

# Debian install will pick this up from /etc/clearwater/config 
SIP_DIGEST_REALM = MUST_BE_CONFIGURED
SPROUT_HOSTNAME = MUST_BE_CONFIGURED

# We use this key to encrypt sensitive fields in the database that we can't
# avoid storing.  In general, we'd like to store passwords as bcrypt hashes
# but we can only do that if the password is sent to us by the user in the 
# clear.  Encrypting the password in the DB at least mitigates DB injection
# attacks and prevents accidental exposure to staff.
#
# Debian install will pick this up from /etc/clearwater/config
PASSWORD_ENCRYPTION_KEY = MUST_BE_CONFIGURED
