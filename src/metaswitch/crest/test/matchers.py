# @file matchers.py
#
# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


class DictContaining(object):
    """Matcher that checks a function argument is a dictionary containing the
    specified key-value pairs (among others)"""
    def __init__(self, mapping):
        self._mapping = mapping

    def __eq__(self, other):
        try:
            return all((other[k] == self._mapping[k]) for k in self._mapping)
        except:
            return False

    def __repr__(self):
        return "<Dictionary containing: %s>" % self._mapping


class ListContaining(object):
    """Matcher that checks a function argument is a list containing the
    specified items (among others)"""
    def __init__(self, items):
        self._items = items

    def __eq__(self, other):
        return all(i in other for i in self._items)

    def __repr__(self):
        return "<List containing: %s>" % self._items


class MatchesAnything(object):
    def __eq__(self, other):
        return True

class MatchesNone(object):
    def __eq__(self, other):
        return (other is None)

