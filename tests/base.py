# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import random
import sys

# Project imports
import posix_ipc

IS_PY3 = (sys.version_info[0] == 3)


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
