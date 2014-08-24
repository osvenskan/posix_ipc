# Python imports
from __future__ import division
import unittest
import datetime
import mmap

# Project imports
import posix_ipc
import base as tests_base

class TestMemory(tests_base.Base):
    SIZE = 1024

    def setUp(self):
        self.mem = posix_ipc.SharedMemory('/foo', posix_ipc.O_CREX,
                                          size=self.SIZE)

    def tearDown(self):
        if self.mem:
            self.mem.close_fd()
            self.mem.unlink()

    def test_no_flags(self):
        """tests that opening a memory segment with no flags opens the existing
        memory and doesn't create a new segment"""
        mem_copy = posix_ipc.SharedMemory('/foo')
        self.assertEqual(self.mem.name, mem_copy.name)

    def test_o_creat_existing(self):
        """tests posix_ipc.O_CREAT to open an existing segment without
        O_EXCL"""
        mem_copy = posix_ipc.SharedMemory('/foo', posix_ipc.O_CREAT)

        self.assertEqual(self.mem.name, mem_copy.name)

    def test_o_creat_new(self):
        """tests posix_ipc.O_CREAT to create a new mem segment without O_EXCL"""
        mem = posix_ipc.SharedMemory('/bar', posix_ipc.O_CREAT)

        # I would prefer this syntax, but it doesn't work with Python < 2.7.
        #self.assertIsNotNone(mem)

        mem.unlink()

    def test_o_excl(self):
        """tests O_CREAT | O_EXCL prevents opening an existing memory segment"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          '/foo', posix_ipc.O_CREAT | posix_ipc.O_EXCL)

    def test_o_crex(self):
        """tests O_CREX prevents opening an existing memory segment"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          '/foo', posix_ipc.O_CREX)

    def test_randomly_generated_name(self):
        """tests that the randomly-generated name works"""
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=1024)
        self.assertIsNotNone(mem.name)
        self.assertEqual(mem.name[0], '/')
        self.assertGreaterEqual(len(mem.name), 2)
        # import pdb
        # pdb.set_trace()

        mem.close_fd()
        mem.unlink()

    # # don't bother testing mode, it's ignored by the OS?

    # Other SharedMemory flags are tested later.

    def test_xxxxx(self):
        """tests xxxxxx"""

        f = mmap.mmap(self.mem.fd, self.SIZE)

        s = f.read(self.SIZE)

        self.assertEqual(f.size(), self.SIZE)

        f.close()




    # def test_zero_initial_value(self):
    #     """tests that the initial value is 0 when assigned"""
    #     if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
    #         sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=0)
    #         self.assertEqual(sem.value, 0)
    #         sem.unlink()

    # def test_nonzero_initial_value(self):
    #     """tests that the initial value is non-zero when assigned"""
    #     if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
    #         sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=42)
    #         self.assertEqual(sem.value, 42)
    #         sem.unlink()


    # # test sacquisition
    # def test_simple_acquisition(self):
    #     """tests that acquisition works"""
    #     # I should be able to acquire this semaphore, but if I can't I don't
    #     # want to hang the test. Acquiring with timeout=0 will raise a BusyError
    #     # if the semaphore can't be acquired. That works even when
    #     # SEMAPHORE_TIMEOUT_SUPPORTED is False.
    #     self.mem.acquire(0)

    # # test acquisition failures
    # # def test_acquisition_no_timeout(self):
    # # This is hard to test since it should wait infinitely. Probably the way
    # # to do it is to spawn another process that holds the semaphore for
    # # maybe 10 seconds and have this process wait on it. That's complicated
    # # and not a really great test.

    # def test_acquisition_zero_timeout(self):
    #     """tests that acquisition w/timeout=0 implements non-blocking
    #     behavior"""
    #     # Should not raise an error
    #     self.mem.acquire(0)

    #     with self.assertRaises(posix_ipc.BusyError):
    #         self.mem.acquire(0)

    # def test_acquisition_nonzero_int_timeout(self):
    #     """tests that acquisition w/timeout=an int is reasonably accurate"""
    #     if posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED:
    #         # Should not raise an error
    #         self.mem.acquire(0)

    #         # This should raise a busy error
    #         wait_time = 1
    #         start = datetime.datetime.now()
    #         with self.assertRaises(posix_ipc.BusyError):
    #             self.mem.acquire(wait_time)
    #         end = datetime.datetime.now()
    #         actual_delta = end - start
    #         expected_delta = datetime.timedelta(seconds=wait_time)

    #         delta = actual_delta - expected_delta

    #         self.assertEqual(delta.days, 0)
    #         self.assertEqual(delta.seconds, 0)
    #         # I don't want to test microseconds because that granularity
    #         # isn't under the control of this module.
    #     # else:
    #         # Can't test this!

    # def test_acquisition_nonzero_float_timeout(self):
    #     """tests that acquisition w/timeout=a float is reasonably accurate"""
    #     if posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED:
    #         # Should not raise an error
    #         self.mem.acquire(0)

    #         # This should raise a busy error
    #         wait_time = 1.5
    #         start = datetime.datetime.now()
    #         with self.assertRaises(posix_ipc.BusyError):
    #             self.mem.acquire(wait_time)
    #         end = datetime.datetime.now()
    #         actual_delta = end - start
    #         expected_delta = datetime.timedelta(seconds=wait_time)

    #         delta = actual_delta - expected_delta

    #         self.assertEqual(delta.days, 0)
    #         self.assertEqual(delta.seconds, 0)
    #         # I don't want to test microseconds because that granularity
    #         # isn't under the control of this module.
    #     # else:
    #         # Can't test this!

    # def test_release(self):
    #     """tests that release works"""
    #     # Not only does it work, I can do it as many times as I want!
    #     for i in range(posix_ipc.SEMAPHORE_VALUE_MAX):
    #         self.mem.release()

    # def test_context_manager(self):
    #     """tests that context manager acquire/release works"""
    #     with self.mem as sem:
    #         if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
    #             self.assertEqual(sem.value, 0)
    #         with self.assertRaises(posix_ipc.BusyError):
    #             sem.acquire(0)

    #     if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
    #         self.assertEqual(sem.value, 0)

    #     # Should not raise an error.
    #     sem.acquire(0)

if __name__ == '__main__':
    unittest.main()
