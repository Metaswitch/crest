# @file __init__.py
#
# Copyright (C) Metaswitch Networks 2013
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.


# This bit of magic turns this package into a namespace package, allowing us to
# have metaswitch.common and metaswitch.ellis etc. in different eggs.
import pkg_resources
pkg_resources.declare_namespace(__name__)
