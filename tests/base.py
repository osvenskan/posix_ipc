# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import random
import sys

# Project imports
import posix_ipc
import utils_for_py26

IS_PY3 = (sys.version_info[0] == 3)
IS_PY_LT_27 = ((sys.version_info[0] == 2) and (sys.version_info[1] < 7))

def make_name():
    """Generate a random name suitable for an IPC object."""
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    return '/' + ''.join(random.sample(alphabet, random.randint(3, 12)))

class Base(unittest.TestCase):
    """Base class for test cases.

    Under Python < 2.7, there's some handy unittest methods that aren't
    defined, so I define them here. They are assertIsNotNone,
    assertGreaterEqual, assertIn, and assertIsInstance. I also redefine
    assertRaises() so that it can be used in a context manager. The
    implementation of each is copied directly from Python's source.
    """
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

    if IS_PY_LT_27:
        # Python < 2.7 has assertRaises(), but it can't be used as a
        # context manager. This version (copied from the Python 2.7
        # standard library) implements a context manager.
        def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
            context = utils_for_py26._AssertRaisesContext(excClass, self)
            if callableObj is None:
                return context
            with context:
                callableObj(*args, **kwargs)

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
                standardMsg = '%s not greater than or equal to %s' % (utils_for_py26._safe_repr(a), utils_for_py26._safe_repr(b))
                self.fail(self._formatMessage(msg, standardMsg))

    if not hasattr(unittest.TestCase, 'assertIn'):
        def assertIn(self, member, container, msg=None):
            """Just like self.assertTrue(a in b), but with a nicer default message."""
            if member not in container:
                standardMsg = '%s not found in %s' % (utils_for_py26._safe_repr(member),
                                                      utils_for_py26._safe_repr(container))
                self.fail(self._formatMessage(msg, standardMsg))

    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, cls, msg=None):
            """Same as self.assertTrue(isinstance(obj, cls)), with a nicer
            default message."""
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (utils_for_py26._safe_repr(obj), cls)
                self.fail(self._formatMessage(msg, standardMsg))

