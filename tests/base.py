# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import random
import sys

# Project imports
import posix_ipc

IS_PY3 = (sys.version_info[0] == 3)

# Swiped from Python 2.7 unittest.util. It's only called when the standard
# lib version doesn't exist (i.e. in Python <= 2.6).
_MAX_LENGTH = 80
def safe_repr(obj, short=False):
    try:
        result = repr(obj)
    except Exception:
        result = object.__repr__(obj)
    if not short or len(result) < _MAX_LENGTH:
        return result
    return result[:_MAX_LENGTH] + ' [truncated]...'


def make_name():
    """Generate a random name suitable for an IPC object."""
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    return '/' + ''.join(random.sample(alphabet, random.randint(3, 12)))


class Base(unittest.TestCase):
    # Under Python < 2.7, there's some handy unittest methods that aren't
    # defined, so I define them here. This code is swiped from Python's source.
    if not hasattr(unittest.TestCase, 'assertIsNotNone'):
        def assertIsNotNone(self, obj, msg=None):
            """Included for symmetry with assertIsNone."""
            if obj is None:
                standardMsg = 'unexpectedly None'
                self.fail(self._formatMessage(msg, standardMsg))

    if not hasattr(unittest.TestCase, 'assertGreaterEqual'):
        def assertGreaterEqual(self, a, b, msg=None):
            """Just like self.assertTrue(a >= b), but with a nicer default message."""
            if not a >= b:
                standardMsg = '%s not greater than or equal to %s' % (safe_repr(a), safe_repr(b))
                self.fail(self._formatMessage(msg, standardMsg))

    if not hasattr(unittest.TestCase, 'assertIn'):
        def assertIn(self, member, container, msg=None):
            """Just like self.assertTrue(a in b), but with a nicer default message."""
            if member not in container:
                standardMsg = '%s not found in %s' % (safe_repr(member),
                                                      safe_repr(container))
                self.fail(self._formatMessage(msg, standardMsg))

    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, cls, msg=None):
            """Same as self.assertTrue(isinstance(obj, cls)), with a nicer
            default message."""
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
                self.fail(self._formatMessage(msg, standardMsg))

