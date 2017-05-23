# @file utils.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


def return_values(*values):
    """
    Create a Mock side_effect function that returns the given
    sequence of values.
    """
    values_copy = list(values)
    def side_effect():
        val = values_copy.pop(0)
        if isinstance(val, Exception):
            raise val
        else:
            return val
    return side_effect
