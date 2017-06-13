#!/usr/bin/env python

# @file main.py
#
# Copyright (C) Metaswitch Networks 2016
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


import os
import argparse
import logging
import prctl
import signal
from sys import executable, exit
from socket import AF_INET
from fcntl import flock, LOCK_EX, LOCK_NB

import cyclone.options
import cyclone.web
import twisted.internet.address
from twisted.internet import reactor

from metaswitch.crest import api
from metaswitch.crest import settings
from metaswitch.common import utils, logging_config
from metaswitch.crest import pdlogs
import syslog

_log = logging.getLogger("crest")
_lock_fd = None

def bind_safely(reactor, process_id, application):
    unix_sock_name = settings.HTTP_UNIX + "-" + str(process_id)
    unix_sock_lock_name = unix_sock_name + ".lockfile"
    fd = open(unix_sock_lock_name, "a+")
    try:
        flock(fd, LOCK_EX | LOCK_NB)
    except IOError:
        _log.error("Lock %s is held by another process, exiting", unix_sock_lock_name)
        exit(1)

    if os.path.exists(unix_sock_name):
        _log.warning("UNIX socket %s exists, but lock %s is not held - deleting stale %s", unix_sock_name, unix_sock_lock_name, unix_sock_name)
        os.remove(unix_sock_name)

    _log.info("Going to listen for HTTP on UNIX socket %s", unix_sock_name)
    reactor.listenUNIX(unix_sock_name, application)
    return fd

def on_before_shutdown():
    pdlogs.CREST_SHUTTING_DOWN.log()
    api.base.shutdownStats()

def on_twisted_log(eventDict):
    text = twisted.python.log.textFromEventDict(eventDict)
    if text is None:
        return
    if eventDict['isError'] or eventDict.get('level', 0) >= logging.ERROR:
        fmtDict = {'text': text.replace("\n", "\n\t")}
        msgStr = twisted.python.log._safeFormat("twisted %(text)s\n", fmtDict)
        pdlogs.TWISTED_ERROR.log(error=msgStr)

def create_application():
    app_settings = {
        "gzip": True,
        "cookie_secret": settings.COOKIE_SECRET,
        "debug": settings.CYCLONE_DEBUG,
    }
    application = cyclone.web.Application(api.get_routes(), **app_settings)

    # Initialize all modules
    api.initialize(application)
    return application

def standalone():
    """
    Initializes Tornado and our application.  Forks worker processes to handle
    requests.  Does not return until all child processes exit normally.
    """
    # Hack to work-around issue with Cyclone and UNIX domain sockets
    twisted.internet.address.UNIXAddress.host = "localhost"

    # Parse arguments
    parser = argparse.ArgumentParser(description="Crest web server")
    parser.add_argument("--background", action="store_true", help="Detach and run server in background")
    parser.add_argument("--signaling-namespace", action="store_true", help="Server running in signaling namespace")
    parser.add_argument("--worker-processes", default=1, type=int)
    parser.add_argument("--shared-http-tcp-fd", default=None, type=int)
    parser.add_argument("--process-id", default=0, type=int)
    parser.add_argument("--log-level", default=2, type=int)
    args = parser.parse_args()

    # Set process name.
    prctl.prctl(prctl.NAME, settings.PROCESS_NAME)

    # We don't initialize logging until we fork because we want each child to
    # have its own logging and it's awkward to reconfigure logging that is
    # defined by the parent.
    application = create_application()

    if args.background:
        # Get a new logfile, rotating the old one if present.
        err_log_name = os.path.join(settings.LOGS_DIR, settings.LOG_FILE_PREFIX + "-err.log")
        try:
            os.rename(err_log_name, err_log_name + ".old")
        except OSError:
            pass
        # Fork into background.
        utils.daemonize(err_log_name)

    utils.install_sigusr1_handler(settings.LOG_FILE_PREFIX)

    # Setup logging
    syslog.openlog(settings.LOG_FILE_PREFIX, syslog.LOG_PID)

    logging_config.configure_logging(
            utils.map_clearwater_log_level(args.log_level),
            settings.LOGS_DIR,
            settings.LOG_FILE_PREFIX,
            args.process_id)

    twisted.python.log.addObserver(on_twisted_log)

    pdlogs.CREST_STARTING.log()

    # setup accumulators and counters for statistics gathering
    api.base.setupStats(args.process_id, args.worker_processes)

    # Initialize reactor ports and create worker sub-processes
    if args.process_id == 0:
        # Main process startup, create pidfile.

        # We must keep a reference to the file object here, as this keeps
        # the file locked and provides extra protection against two processes running at
        # once.
        pidfile_lock = None
        try:
            pidfile_lock = utils.lock_and_write_pid_file(settings.PID_FILE) # noqa
        except IOError:
            # We failed to take the lock - another process is already running
            exit(1)

        # Create UNIX domain socket for nginx front-end (used for
        # normal operation and as a bridge from the default namespace to the signaling
        # namespace in a multiple interface configuration).
        bind_safely(reactor, args.process_id, application)
        pdlogs.CREST_UP.log()

        if args.signaling_namespace and settings.PROCESS_NAME == "homer":
            # Running in signaling namespace as Homer, create TCP socket for XDMS requests
            # from signaling interface
            _log.info("Going to listen for HTTP on TCP port %s", settings.HTTP_PORT)
            http_tcp_port = reactor.listenTCP(settings.HTTP_PORT, application, interface=settings.LOCAL_IP)

            # Spin up worker sub-processes, passing TCP file descriptor
            for process_id in range(1, args.worker_processes):
                reactor.spawnProcess(None, executable, [executable, __file__,
                                     "--shared-http-tcp-fd", str(http_tcp_port.fileno()),
                                     "--process-id", str(process_id)],
                                     childFDs={0: 0, 1: 1, 2: 2, http_tcp_port.fileno(): http_tcp_port.fileno()},
                                     env = os.environ)
        else:
            # Spin up worker sub-processes
            for process_id in range(1, args.worker_processes):
                reactor.spawnProcess(None, executable, [executable, __file__,
                                     "--process-id", str(process_id)],
                                     childFDs={0: 0, 1: 1, 2: 2},
                                     env = os.environ)
    else:
        # Sub-process startup, ensure we die if our parent does.
        prctl.prctl(prctl.PDEATHSIG, signal.SIGTERM)

        # Create UNIX domain socket for nginx front-end based on process ID.
        bind_safely(reactor, args.process_id, application)

        # Create TCP socket if file descriptor was passed.
        if args.shared_http_tcp_fd:
            reactor.adoptStreamPort(args.shared_http_tcp_fd, AF_INET, application)

    # We need to catch the shutdown request so that we can properly stop
    # the ZMQ interface; otherwise the reactor won't shut down on a SIGTERM
    # and will be SIGKILLed when the service is stopped.
    reactor.addSystemEventTrigger('before', 'shutdown', on_before_shutdown)

    # Kick off the reactor to start listening on configured ports
    reactor.run()

if __name__ == '__main__':
    standalone()
