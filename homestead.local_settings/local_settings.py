# @file local_settings.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

PROCESS_NAME="homestead-prov"
LOGS_DIR = "/var/log/homestead-prov"
PID_FILE = "/var/run/homestead-prov.pid"
LOG_FILE_PREFIX = "homestead-prov"
INSTALLED_HANDLERS = ["homestead_prov"]
HTTP_PORT = 8889
HTTP_UNIX = "/tmp/.homestead-prov-sock"
ZMQ_PORT = 6667

# Debian install will pick this up from /etc/clearwater/config
CASS_HOST = "localhost"

# Debian install will pick this up from /etc/clearwater/config
LOCAL_IP = MUST_BE_CONFIGURED
SIP_DIGEST_REALM = MUST_BE_CONFIGURED
SPROUT_HOSTNAME = MUST_BE_CONFIGURED
PUBLIC_HOSTNAME = MUST_BE_CONFIGURED
HS_HOSTNAME = MUST_BE_CONFIGURED
CCF = ""

# We use this key to encrypt sensitive fields in the database that we can't
# avoid storing.  In general, we'd like to store passwords as bcrypt hashes
# but we can only do that if the password is sent to us by the user in the
# clear.  Encrypting the password in the DB at least mitigates DB injection
# attacks and prevents accidental exposure to staff.
#
# Debian install will pick this up from /etc/clearwater/config
PASSWORD_ENCRYPTION_KEY = MUST_BE_CONFIGURED
