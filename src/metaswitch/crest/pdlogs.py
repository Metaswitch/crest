# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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
    cause="The service has successfully started.",
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
