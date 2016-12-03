# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import random
import sys
import platform

# Project imports

IS_PY3 = (sys.version_info[0] == 3)


def _force_int(a_string):
    """Return the string as an int. If it can't be made into an int, return 0."""
    try:
        an_int = int(a_string)
    except (ValueError, TypeError):
        an_int = 0

    return an_int


# Lots of code here to determine if the FreeBSD version is <= 10.2. Those versions contain a
# bug that causes a hang or seg fault if I exercise certain portions of the semaphore tests.
IS_FREEBSD = (platform.system().lower() == 'freebsd')
FREEBSD_VERSION_MINOR = 0
FREEBSD_VERSION_MAJOR = 0

if IS_FREEBSD:
    # I want to get the release number. Here's some samples of what I've seen in platform.release():
    # PC BSD 10.2: '10.2-RELEASE-p14'
    # FreeBSD 9.1: '9.1-RELEASE-p7'
    # I want the number at the beginning. The code below attempts to extract it, but if it runs
    # into anything unexpected it stops trying rather than raising an error.
    release = platform.release().split('-')[0]
    if '.' in release:
        major, minor = release.split('.', 2)
        FREEBSD_VERSION_MAJOR = _force_int(major)
        FREEBSD_VERSION_MINOR = _force_int(minor)
    # else:
        # This isn't in the format I expect, so I don't try to parse it.

# https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=206396
HAS_FREEBSD_BUG_206396 = IS_FREEBSD and (FREEBSD_VERSION_MAJOR <= 10) and \
                         (FREEBSD_VERSION_MINOR <= 2)
FREEBSD_BUG_206396_SKIP_MSG = \
    'Feature buggy on this platform; see https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=206396'


def make_name():
    """Generate a random name suitable for an IPC object."""
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    return '/' + ''.join(random.sample(alphabet, random.randint(3, 12)))


class Base(unittest.TestCase):
    """Base class for test cases."""
    def assertWriteToReadOnlyPropertyFails(self, target_object, property_name,
                                           value):
        """test that writing to a readonly property raises an exception"""
        # The attributes tested with this code are implemented differently in C.
        # For instance, Semaphore.value is a 'getseters' with a NULL setter,
        # whereas Semaphore.name is a reference into the Semaphore member
        # definition.
        # Under Python 2.6, writing to sem.value raises AttributeError whereas
        # writing to sem.name raises TypeError. Under Python 3, both raise
        # AttributeError (but with different error messages!).
        # This illustrates that Python is a little unpredictable in this
        # matter. Rather than testing each of the numerous combinations of
        # of Python versions and attribute implementation, I just accept
        # both TypeError and AttributeError here.
        # ref: http://bugs.python.org/issue1687163
        # ref: http://bugs.python.org/msg127173
        with self.assertRaises((TypeError, AttributeError)):
            setattr(target_object, property_name, value)
