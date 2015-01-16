# @file exceptions.py
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

# HSS-specific Exceptions
class HSSNotEnabled(Exception):
    """Exception to throw if gateway is created without a valid HSS_IP"""
    pass

class HSSOverloaded(Exception):
    """Exception to throw if a request cannot be completed because the HSS returns an
    overloaded response"""
    pass

class HSSConnectionLost(Exception):
    """Exception to throw if we have lost our HSS connection"""
    pass

class HSSStillConnecting(Exception):
    """Exception to throw if we have lost our HSS connection"""
    pass

# User-specific Exceptions
class UserNotIdentifiable(Exception):
    """Exception to throw if we are unable to identify a user"""
    pass

class UserNotAuthorized(Exception):
    """Exception to throw if we are unable to authorize a user"""
    pass

# IRS-specific Exceptions
class IRSNoSIPURI(Exception):
    """Exception to throw if we are creating an IRS with no SIP URI"""
    pass
