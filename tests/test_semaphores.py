# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
from unittest import skipUnless
import datetime

# Project imports
import posix_ipc
# Hack -- add tests directory to sys.path so Python 3 can find base.py.
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
import base as tests_base  # noqa


# N_RELEASES is the number of times release() is called in test_release()
N_RELEASES = 1000000  # 1 million


class SemaphoreTestBase(tests_base.Base):
    """base class for Semaphore test classes"""
    def setUp(self):
        self.sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=1)

    def tearDown(self):
        if self.sem:
            self.sem.unlink()

    def assertWriteToReadOnlyPropertyFails(self, property_name, value):
        """test that writing to a readonly property raises TypeError"""
        tests_base.Base.assertWriteToReadOnlyPropertyFails(self, self.sem, property_name, value)


class TestSemaphoreCreation(SemaphoreTestBase):
    """Exercise stuff related to creating Semaphores"""
    def test_no_flags(self):
        """tests that opening a semaphore with no flags opens the existing
        semaphore and doesn't create a new semaphore"""
        sem_copy = posix_ipc.Semaphore(self.sem.name)
        self.assertEqual(self.sem.name, sem_copy.name)

    def test_o_creat_existing(self):
        """tests posix_ipc.O_CREAT to open an existing semaphore without
        O_EXCL"""
        sem_copy = posix_ipc.Semaphore(self.sem.name, posix_ipc.O_CREAT)

        self.assertEqual(self.sem.name, sem_copy.name)

    def test_o_creat_new(self):
        """tests posix_ipc.O_CREAT to create a new semaphore without O_EXCL"""
        # I can't pass None for the name unless I also pass O_EXCL.
        name = tests_base.make_name()

        # Note: this method of finding an unused name is vulnerable to a race
        # condition. It's good enough for test, but don't copy it for use in
        # production code!
        name_is_available = False
        while not name_is_available:
            try:
                sem = posix_ipc.Semaphore(name)
                sem.close()
            except posix_ipc.ExistentialError:
                name_is_available = True
            else:
                name = tests_base.make_name()

        sem = posix_ipc.Semaphore(name, posix_ipc.O_CREAT)

        self.assertIsNotNone(sem)

        sem.unlink()

    @unittest.skipIf(tests_base.HAS_FREEBSD_BUG_206396, tests_base.FREEBSD_BUG_206396_SKIP_MSG)
    def test_o_excl(self):
        """tests O_CREAT | O_EXCL prevents opening an existing semaphore"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.Semaphore,
                          self.sem.name, posix_ipc.O_CREAT | posix_ipc.O_EXCL)

    @unittest.skipIf(tests_base.HAS_FREEBSD_BUG_206396, tests_base.FREEBSD_BUG_206396_SKIP_MSG)
    def test_o_crex(self):
        """tests O_CREX prevents opening an existing semaphore"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.Semaphore,
                          self.sem.name, posix_ipc.O_CREX)

    def test_randomly_generated_name(self):
        """tests that the randomly-generated name works"""
        # This is tested implicitly elsewhere but I want to test it explicitly
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX)
        self.assertIsNotNone(sem.name)

        self.assertEqual(sem.name[0], '/')
        self.assertGreaterEqual(len(sem.name), 2)
        sem.unlink()

    def test_name_as_bytes(self):
        """Test that the name can be bytes.

        In Python 2, bytes == str. This test is really only interesting in Python 3.
        """
        if tests_base.IS_PY3:
            name = bytes(tests_base.make_name(), 'ASCII')
        else:
            name = bytes(tests_base.make_name())
        sem = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
        # No matter what the name is passed as, posix_ipc.name returns the default string type,
        # i.e. str in Python 2 and unicode in Python 3.
        if tests_base.IS_PY3:
            self.assertEqual(name, bytes(sem.name, 'ASCII'))
        else:
            self.assertEqual(name, sem.name)
        sem.unlink()
        sem.close()

    def test_name_as_unicode(self):
        """Test that the name can be unicode.

        In Python 3, str == unicode. This test is really only interesting in Python 2.
        """
        if tests_base.IS_PY3:
            name = tests_base.make_name()
        else:
            name = tests_base.make_name().decode('ASCII')
        sem = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
        self.assertEqual(name, sem.name)
        sem.unlink()
        sem.close()

    # don't bother testing mode, it's ignored by the OS?

    @skipUnless(posix_ipc.SEMAPHORE_VALUE_SUPPORTED, "Requires Semaphore.value support")
    def test_default_initial_value(self):
        """tests that the initial value is 0 by default"""
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX)
        self.assertEqual(sem.value, 0)
        sem.unlink()

    @skipUnless(posix_ipc.SEMAPHORE_VALUE_SUPPORTED, "Requires Semaphore.value support")
    def test_zero_initial_value(self):
        """tests that the initial value is 0 when assigned"""
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=0)
        self.assertEqual(sem.value, 0)
        sem.unlink()

    @skipUnless(posix_ipc.SEMAPHORE_VALUE_SUPPORTED, "Requires Semaphore.value support")
    def test_nonzero_initial_value(self):
        """tests that the initial value is non-zero when assigned"""
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=42)
        self.assertEqual(sem.value, 42)
        sem.unlink()

    def test_kwargs(self):
        """ensure init accepts keyword args as advertised"""
        # mode 0x180 = 0600. Octal is difficult to express in Python 2/3 compatible code.
        sem = posix_ipc.Semaphore(None, flags=posix_ipc.O_CREX, mode=0x180, initial_value=0)
        sem.unlink()


class TestSemaphoreAquisitionAndRelease(SemaphoreTestBase):
    """Exercise acquiring & releasing semaphores"""
    def test_simple_acquisition(self):
        """tests that acquisition works"""
        self.sem.acquire()

    # test acquisition failures
    # def test_acquisition_no_timeout(self):
    # FIXME
    # This is hard to test since it should wait infinitely. Probably the way
    # to do it is to spawn another process that holds the semaphore for
    # maybe 10 seconds and have this process wait on it. That's complicated
    # and not a really great test.

    def test_acquisition_zero_timeout(self):
        """tests that acquisition w/timeout=0 implements non-blocking
        behavior"""
        # Should not raise an error
        self.sem.acquire(0)
        with self.assertRaises(posix_ipc.BusyError):
            self.sem.acquire(0)

    @skipUnless(posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED, "Requires Semaphore timeout support")
    def test_acquisition_nonzero_int_timeout(self):
        """tests that acquisition w/timeout=an int is reasonably accurate"""
        # Should not raise an error
        self.sem.acquire(0)

        # This should raise a busy error
        wait_time = 1
        start = datetime.datetime.now()
        with self.assertRaises(posix_ipc.BusyError):
            self.sem.acquire(wait_time)
        end = datetime.datetime.now()
        actual_delta = end - start
        expected_delta = datetime.timedelta(seconds=wait_time)

        delta = actual_delta - expected_delta

        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 0)
        # I don't want to test microseconds because that granularity
        # isn't under the control of this module.

    @skipUnless(posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED, "Requires Semaphore timeout support")
    def test_acquisition_nonzero_float_timeout(self):
        """tests that acquisition w/timeout=a float is reasonably accurate"""
        # Should not raise an error
        self.sem.acquire(0)

        # This should raise a busy error
        wait_time = 1.5
        start = datetime.datetime.now()
        with self.assertRaises(posix_ipc.BusyError):
            self.sem.acquire(wait_time)
        end = datetime.datetime.now()
        actual_delta = end - start
        expected_delta = datetime.timedelta(seconds=wait_time)

        delta = actual_delta - expected_delta

        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 0)
        # I don't want to test microseconds because that granularity
        # isn't under the control of this module.

    def test_release(self):
        """tests that release works"""
        # Not only does it work, I can do it as many times as I want! I had
        # tried some code that called release() SEMAPHORE_VALUE_MAX times, but
        # on platforms where that's ~2 billion, the test takes too long to run.
        # So I'll stick to a lower (but still very large) number of releases.
        n_releases = min(N_RELEASES, posix_ipc.SEMAPHORE_VALUE_MAX - 1)
        for i in range(n_releases):
            self.sem.release()

    def test_context_manager(self):
        """tests that context manager acquire/release works"""
        with self.sem as sem:
            if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
                self.assertEqual(sem.value, 0)
            with self.assertRaises(posix_ipc.BusyError):
                sem.acquire(0)

        if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
            self.assertEqual(sem.value, 1)

        # Should not raise an error.
        sem.acquire(0)


class TestSemaphoreDestruction(SemaphoreTestBase):
    def test_close_and_unlink(self):
        """tests that sem.close() and sem.unlink() work"""
        # sem.close() is hard to test since subsequent use of the semaphore
        # after sem.close() is undefined. All I can think of to do is call it
        # and note that it does not fail. Also, it allows sem.unlink() to
        # tell the OS to delete the semaphore entirely, so it makes sense
        # to test them together.
        self.sem.unlink()
        self.sem.close()
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.Semaphore,
                          self.sem.name)
        # Wipe this out so that self.tearDown() doesn't crash.
        self.sem = None


class TestSemaphorePropertiesAndAttributes(SemaphoreTestBase):
    def test_property_name(self):
        """exercise Semaphore.name"""
        self.assertGreaterEqual(len(self.sem.name), 2)

        self.assertEqual(self.sem.name[0], '/')

        self.assertWriteToReadOnlyPropertyFails('name', 'hello world')

    @skipUnless(posix_ipc.SEMAPHORE_VALUE_SUPPORTED, "Requires Semaphore.value support")
    def test_property_value(self):
        """exercise Semaphore.value if possible"""
        # test read, although this has been tested very thoroughly above
        self.assertEqual(self.sem.value, 1)

        self.assertWriteToReadOnlyPropertyFails('value', 42)


if __name__ == '__main__':
    unittest.main()
