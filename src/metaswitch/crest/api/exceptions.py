# @file exceptions.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

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
