# @file setup_crest.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import logging
import sys
# Workaround bug in multiprocessing - http://bugs.python.org/issue15881
# Without this, running tests involving twisted throws an error on completion
try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages
from logging import StreamHandler

_log = logging.getLogger("crest")
_log.setLevel(logging.DEBUG)
_handler = StreamHandler(sys.stderr)
_handler.setLevel(logging.DEBUG)
_log.addHandler(_handler)

setup(
    name='crest',
    version='0.1',
    namespace_packages = ['metaswitch'],
    packages=find_packages('src', include=['metaswitch', 'metaswitch.crest', 'metaswitch.crest.*']),
    package_dir={'':'src'},
    test_suite='metaswitch.crest.test',
    install_requires=[
        "asn1crypto==0.22.0",
        "attrs==17.2.0",
        "Automat==0.6.0",
        "constantly==15.1.0",
        "cql==1.4.0",
        "cryptography==1.9",
        "cyclone==1.0",
        "enum34==1.1.6",
        "idna==2.5",
        "incremental==17.5.0",
        "ipaddress==1.0.18",
        "lxml==3.6.0",
        "msgpack-python==0.4.7",
        "prctl==1.0.1",
        "pure-sasl==0.4.0",
        "pyOpenSSL==17.0.0",
        "setuptools==24.0.0",
        "six==1.10.0",
        "thrift==0.9.3",
        "Twisted==17.1.0",
        "zope.interface==4.4.1"],
     tests_require=[
         "funcsigs==1.0.2",
         "Mock==2.0.0",
         "pbr==1.6",
         "six==1.10.0"],
    options={"build": {"build_base": "build-crest"}},
    )
