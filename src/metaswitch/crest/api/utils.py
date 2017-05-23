# @file utils.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

import itertools


def flatten(list_of_lists):
    """Flatten a list of lists into a single list, e.g:
    flatten([[A, B], [C, D]]) -> [A, B, C, D] """
    return list(itertools.chain.from_iterable(list_of_lists))
