# @file xsd.py
#
# Copyright (C) Metaswitch Networks 2013
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


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
