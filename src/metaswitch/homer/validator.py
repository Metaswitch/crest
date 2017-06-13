# @file validator.py
#
# Copyright (C) Metaswitch Networks 2015
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


import logging

from metaswitch.crest.api.passthrough import PassthroughHandler
from metaswitch.crest.api import xsd

_log = logging.getLogger("crest.api.homer")


def create_handler(schema):

    class ValidationHandler(PassthroughHandler):
        """
        Handler that validates documents before storing them
        """

        @xsd.validate(schema)
        def put(self, *args):
            return PassthroughHandler.put(self, *args)

    return ValidationHandler
