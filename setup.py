# @file setup.py
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
    packages=find_packages('src'),
    package_dir={'':'src'},
    package_data={'': ['*.xsd', 'dictionary.xml']},
    test_suite='metaswitch.crest.test',
    install_requires=["Mock", "py-bcrypt", "cyclone", "cql", "lxml", "msgpack-python"],
    )
