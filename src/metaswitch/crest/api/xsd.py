# @file xsd.py
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


import logging

from lxml import etree
from cyclone.web import HTTPError

_log = logging.getLogger("crest.api")
_parsers = {}


def _validate(xml, schema_path):
    parser = _get_parser(schema_path)
    etree.fromstring(xml, parser)  # Will throw etree.XMLSyntaxError exception on failure
    return True


def _get_parser(schema_path):
    if schema_path in _parsers:
        return _parsers[schema_path]
    else:
        with open(schema_path, 'r') as f:
            parser = etree.XMLParser(schema=etree.XMLSchema(etree.parse(f)))
            return _parsers.setdefault(schema_path, parser)


def validate(schema_path):
    """
    Decorator to validate the request body using an XSD schema.
    Pass the path to the XSD schema file to the decorator and
    then use to decorate a standard cyclone put/post function.
    Note that to call a superclass when using this decorator
    you must explicitly specify it, e.g.

        PassthroughHandler.put(self, *args)

    If the request passes the schema validation the decorated
    handler is called, otherwise a HTTPError(400) is thrown,
    with the reason specified in the log message
    """
    def validate_decorator(func):
        def wrapper(self, *args, **kwargs):
            _log.info("Performing XSD validation")
            try:
                _validate(self.request.body, schema_path)
            except etree.XMLSyntaxError, e:
                raise HTTPError(400, log_message=str(e))
            return func(self, *args, **kwargs)
        return wrapper
    return validate_decorator
