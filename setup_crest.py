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
    install_requires=["pyzmq==16.0.2", "py-bcrypt", "cyclone==1.0", "cql==1.4.0", "lxml==3.6.0", "msgpack-python==0.4.7", "pure-sasl", "prctl", "monotonic==0.6", "thrift==0.9.3"],
    tests_require=["pbr==1.6", "Mock"],
    options={"build": {"build_base": "build-crest"}},
    )
