# Project Clearwater - IMS in the Cloud
# Copyright (C) 2015 Metaswitch Networks Ltd
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

from metaswitch.common.pdlogs import PDLog
from metaswitch.crest import settings

CREST_SHUTTING_DOWN = PDLog(
    number=PDLog.CL_CREST_ID + 1,
    desc="Service '%s' is shutting down." % settings.LOG_FILE_PREFIX,
    cause="A 'shutdown' was requested by an external entity.",
    effect="%s service is no longer available." % settings.LOG_FILE_PREFIX,
    action="Verify that the shutdown request was authorized.",
    priority=PDLog.LOG_NOTICE)

CREST_STARTING = PDLog(
    number=PDLog.CL_CREST_ID + 2,
    desc="Service '%s' is starting." % settings.LOG_FILE_PREFIX,
    cause="A 'start' was requested by an external entity.",
    effect="%s service is starting." % settings.LOG_FILE_PREFIX,
    action="None.",
    priority=PDLog.LOG_NOTICE)

CREST_UP = PDLog(
    number=PDLog.CL_CREST_ID + 3,
    desc="Service '%s' is up and listening for UNIX socket." % (settings.LOG_FILE_PREFIX),
    cause="A shutdown was requested by an external entity.",
    effect="%s service is available." % settings.LOG_FILE_PREFIX,
    action="None.",
    priority=PDLog.LOG_NOTICE)

API_OVERLOADED = PDLog(
    number=PDLog.CL_CREST_ID + 4,
    desc="Service '%s' has become overloaded and rejecting requests." % settings.LOG_FILE_PREFIX,
    cause="The service has received too many requests and has become overloaded.",
    effect="Requests are being rejected.",
    action="Determine the cause of the overload and scale appropriately.",
    priority=PDLog.LOG_NOTICE)

API_NOTOVERLOADED = PDLog(
    number=PDLog.CL_CREST_ID + 5,
    desc="Service '%s' is no longer overloaded and is accepting requests." % settings.LOG_FILE_PREFIX,
    cause="The service is no longer overloaded.",
    effect="Requests are being accepted.",
    action="None.",
    priority=PDLog.LOG_NOTICE)

API_HTTPERROR = PDLog(
    number=PDLog.CL_CREST_ID + 6,
    desc="HTTP error: {error}.",
    cause="The service has hit an error processing an HTTP request.",
    effect="The request has been rejected.",
    action="None.",
    priority=PDLog.LOG_WARNING)

API_UNCAUGHT_EXCEPTION = PDLog(
    number=PDLog.CL_CREST_ID + 7,
    desc="Uncaught exception: {exception}.",
    cause="An unexpected exception has occurred while processing a request.",
    effect="The request has been rejected.",
    action="Ensure that the node has been installed correctly and that it has valid configuration.",
    priority=PDLog.LOG_ERR)

TWISTED_ERROR = PDLog(
    number=PDLog.CL_CREST_ID + 8,
    desc="Internal 'twisted' error: {error}.",
    cause="An unexpected internal error has occurred within the 'Twisted' component.",
    effect="Unknown.",
    action="Ensure that the node has been installed correctly and that it has valid configuration.",
    priority=PDLog.LOG_ERR)
