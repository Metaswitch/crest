# @file local_settings.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

PROCESS_NAME="homer"
LOGS_DIR = "/var/log/homer"
PID_FILE = "/var/run/homer.pid"
LOG_FILE_PREFIX = "homer"
INSTALLED_HANDLERS = ["homer"]
HTTP_PORT = 7888
HTTP_UNIX = "/tmp/.homer-sock"
ZMQ_PORT = 6665

# Debian install will pick this up from /etc/clearwater/config
CASS_HOST = "localhost"

# Debian install will pick this up from /etc/clearwater/config
LOCAL_IP = MUST_BE_CONFIGURED
SIP_DIGEST_REALM = MUST_BE_CONFIGURED
SPROUT_HOSTNAME = MUST_BE_CONFIGURED
