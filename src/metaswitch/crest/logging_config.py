# @file logging_config.py
#
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by post at
# Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK


import os
import logging
import logging.handlers

from metaswitch.crest import settings

def configure_logging(task_id):
    root_log = logging.getLogger()
    root_log.setLevel(logging.DEBUG)
    for h in root_log.handlers:
        root_log.removeHandler(h)
    fmt = logging.Formatter('%(asctime)s %(levelname)1.1s %(module)s:%(lineno)d %(process)d:%(thread)d] %(message)s')
    log_file = os.path.join(settings.LOGS_DIR,
                            "%(prefix)s-%(task_id)s.log" % {"prefix": settings.LOG_FILE_PREFIX, "task_id": task_id})
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   backupCount=settings.LOG_BACKUP_COUNT,
                                                   maxBytes=settings.LOG_FILE_MAX_BYTES)
    handler.setFormatter(fmt)
    handler.setLevel(logging.DEBUG)
    root_log.addHandler(handler)
    print "Logging to %s" % log_file
