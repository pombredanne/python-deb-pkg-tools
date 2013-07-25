# Debian packaging tools: Control file manipulation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 25, 2013
# URL: https://github.com/xolox/python-deb-pkg-tools

"""
Control file manipulation
=========================

The functions in the :py:mod:`deb_pkg_tools.control` module can be used to
manipulate Debian control files. It was developed specifically for control
files of binary packages, however the code is very generic. This module builds
on top of the :py:class:`debian.deb822.Deb822` class from the python-debian_
package.

.. _python-debian: https://pypi.python.org/pypi/python-debian
"""

# Standard library modules.
import logging

# External dependencies.
from debian.deb822 import Deb822

# Initialize a logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Control file fields that are like `Depends:' (they contain a comma
# separated list of package names with optional version specifications).
DEPENDS_LIKE_FIELDS = ('conflicts', 'depends', 'provides', 'replaces', 'suggests')

def merge_control_fields(defaults, overrides):
    """
    Merge the fields of two Debian control files.

    :param defaults: A dictionary with existing control field name/value pairs
                     (may be an instance of :py:class:`debian.deb822.Deb822`
                     but doesn't have to be).
    :param overrides: A dictionary with fields that should override default
                      name/value pairs. Values of the fields `Depends`,
                      `Provides`, `Replaces` and `Conflicts` are merged
                      while values of other fields are overwritten.
    :returns: An instance of :py:class:`debian.deb822.Deb822` that contains the
              merged control field name/value pairs.
    """
    defaults = parse_control_fields(defaults)
    overrides = parse_control_fields(overrides)
    logger.debug("Merging control files (%i default fields, %i override fields)", len(defaults), len(overrides))
    merged = {}
    for name in (set(defaults.keys()) | set(overrides.keys())):
        if name.lower() in DEPENDS_LIKE_FIELDS:
            # Dependencies are merged instead of overridden.
            dependencies = set()
            dependencies.update(defaults.get(name, []))
            dependencies.update(overrides.get(name, []))
            merged[name] = sorted(dependencies, key=lambda s: s.lower())
            logger.debug("Merged field %s: %r", name, merged[name])
        elif name not in overrides:
            logger.debug("Field %s only present in defaults: %r", name, defaults[name])
            merged[name] = defaults[name]
        elif name not in defaults:
            logger.debug("Field %s only present in overrides: %r", name, overrides[name])
            merged[name] = overrides[name]
        else:
            # Field present in both defaults and overrides;
            # in this case the override takes precedence.
            merged[name] = overrides[name]
            logger.debug("Overriding field %s: %r -> %r", name, defaults[name], overrides[name])
    return unparse_control_fields(merged)

def parse_control_fields(input_fields):
    """
    The :py:class:`debian.deb822.Deb822` class can be used to parse Debian
    control files but the result is simple a :py:class:`dict` with string
    name/value pairs. This function takes an existing :py:class:`debian.deb822.Deb822`
    instance and converts known fields into friendlier formats, for example:

    - The value of `Depends`, `Provides`, `Replaces` and `Conflicts` fields is
      converted to a list of strings.

    - The value of the `Installed-Size` field is converted to an integer.

    :param input_fields: The dictionary to convert (may be an instance of
                         :py:class:`debian.deb822.Deb822` but doesn't have
                         to be).
    :returns: A :py:class:`dict` object with the converted fields.

    Here's an example of what the result looks like (to see the unparsed
    values, take a look at the example under :py:func:`deb_pkg_tools.package.inspect_package()`):

    >>> from deb_pkg_tools.control import parse_control_fields
    >>> from deb_pkg_tools.package import inspect_package
    >>> fields = inspect_package('/var/cache/apt/archives/python2.7_2.7.3-0ubuntu3.2_amd64.deb')
    >>> parse_control_fields(fields)
    {'Architecture': u'amd64',
     'Conflicts': [u'python-profiler (<= 2.7.1-2)'],
     'Depends': [u'python2.7-minimal (= 2.7.3-0ubuntu3.2)',
                 u'mime-support',
                 u'libbz2-1.0',
                 u'libc6 (>= 2.15)',
                 u'libdb5.1',
                 u'libexpat1 (>= 1.95.8)',
                 u'libgcc1 (>= 1:4.1.1)',
                 u'libncursesw5 (>= 5.6+20070908)',
                 u'libreadline6 (>= 6.0)',
                 u'libsqlite3-0 (>= 3.5.9)',
                 u'libtinfo5'],
     'Description': u'Interactive high-level object-oriented language ...',
     'Installed-Size': 8779,
     'Maintainer': u'Ubuntu Core Developers <ubuntu-devel-discuss@lists.ubuntu.com>',
     'Multi-Arch': u'allowed',
     'Original-Maintainer': u'Matthias Klose <doko@debian.org>',
     'Package': u'python2.7',
     'Priority': u'optional',
     'Provides': [u'python-argparse',
                  u'python2.7-argparse',
                  u'python2.7-celementtree',
                  u'python2.7-cjkcodecs',
                  u'python2.7-ctypes',
                  u'python2.7-elementtree',
                  u'python2.7-profiler',
                  u'python2.7-wsgiref'],
     'Replaces': [u'python-profiler (<= 2.7.1-2)'],
     'Section': u'python',
     'Suggests': [u'python2.7-doc',
                  u'binutils'],
     'Version': u'2.7.3-0ubuntu3.2'}
    """
    logger.debug("Parsing %i control fields ..", len(input_fields))
    output_fields = {}
    for name, unparsed_value in input_fields.iteritems():
        if name.lower() in DEPENDS_LIKE_FIELDS:
            parsed_value = [s.strip() for s in unparsed_value.split(',') if s and not s.isspace()]
        elif name.lower() == 'installed-size':
            parsed_value = int(unparsed_value)
        else:
            parsed_value = unparsed_value
        if parsed_value != unparsed_value:
            logger.debug("Parsed field %s: %r -> %r", name, unparsed_value, parsed_value)
        else:
            logger.debug("Parsed field %s: %r", name, parsed_value)
        output_fields[name] = parsed_value
    return output_fields

def unparse_control_fields(input_fields):
    """
    Convert a :py:class:`dict` returned by :py:func:`parse_control_fields()`
    back into a :py:class:`debian.deb822.Deb822` object.

    :param input_fields: A :py:class:`dict` object previously returned by
                         :py:func:`parse_control_fields()`.
    :returns: A :py:class:`debian.deb822.Deb822` object.
    """
    logger.debug("Unparsing %i control fields ..", len(input_fields))
    output_fields = Deb822()
    for name, parsed_value in input_fields.iteritems():
        if name.lower() in DEPENDS_LIKE_FIELDS:
            unparsed_value = ', '.join(parsed_value)
        elif name.lower() == 'installed-size':
            unparsed_value = str(parsed_value)
        else:
            unparsed_value = parsed_value
        if unparsed_value != parsed_value:
            logger.debug("Unparsed field %s: %r -> %r", name, parsed_value, unparsed_value)
        else:
            logger.debug("Unparsed field %s: %r", name, unparsed_value)
        output_fields[name] = unparsed_value
    return output_fields

# vim: ts=4 sw=4 et