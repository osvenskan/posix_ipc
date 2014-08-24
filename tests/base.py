# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest

# Project imports
import posix_ipc

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


class Base(unittest.TestCase):

    # Under Python < 2.7, there's some handy unittest methods that aren't
    # defined, so I define them here.
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


