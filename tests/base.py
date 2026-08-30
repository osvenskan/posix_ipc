# Python imports
import unittest
import random
import platform

# PyPy requires some specific test behavior
IS_PYPY = (platform.python_implementation() == 'PyPy')


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
    @staticmethod
    def _get_class_name(an_object):
        '''Return a version of the class name appropriate for assertWriteToReadOnlyPropertyFails().
        This encapsulates a quirk specific to that assertion function. For details, see
        https://github.com/osvenskan/sysv_ipc/issues/68
        '''
        # Extract the class name. str() returns something like this --
        #    <class 'sysv_ipc.SharedMemory'>
        # From that, I only want this bit --
        #    sysv_ipc.SharedMemory
        class_name = str(an_object.__class__)[8:-2]

        # Under PyPy, the module prefix doesn't appear in the exception message that I see in
        # assertWriteToReadOnlyPropertyFails().
        if IS_PYPY:
            class_name = class_name[9:]

        return class_name

    def assertWriteToReadOnlyPropertyFails(self, target_object, property_name, value):
        """test that writing to a readonly property raises an exception with the expected msg"""
        with self.assertRaises(AttributeError) as context:
            setattr(target_object, property_name, value)

        # In addition to checking that AttributeError is raised, I also check the message text.
        # I don't understand why, but for some attributes the message is 'readonly attribute',
        # and for others it is more specific. Rather than trying to figure out which to expect,
        # this test accepts both.
        actual = str(context.exception)

        class_name = self._get_class_name(target_object)
        expected = (
            'readonly attribute',
            f"attribute '{property_name}' of '{class_name}' objects is not writable"
        )

        assert (actual in expected),  f'actual: `{actual}`, expected: `{expected}`'
