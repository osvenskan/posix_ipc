# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import datetime
import mmap
import os

# Project imports
import posix_ipc
import base as tests_base

class TestMemory(tests_base.Base):
    # SIZE should be something that's not a power of 2 since that's more
    # likely to expose odd behavior.
    SIZE = 3333

    def get_block_size(self):
        """Return block size as reported by operating system"""
        # I thought it would be a good idea to pass self.mem.name to
        # os.statvfs in case that filesystem is different from the
        # regular one, but I get 'No such file or directory' when I do so.
        # This happens on OS X and Linux.
        return os.statvfs('.')[1]

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

        self.assertIsNotNone(mem)

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
        mem.close_fd()
        mem.unlink()

    # # don't bother testing mode, it's ignored by the OS?

    # Other SharedMemory flags are tested later.

    def test_mmap_size(self):
        """tests that the size specified is (somewhat) respected by mmap()"""
        # In limited testing, Linux respects the exact size specified in the
        # SharedMemory() ctor when creating the mmapped file.
        # e.g. when self.SIZE = 3333, the
        # mmapped file is also 3333 bytes.
        #
        # OS X's mmapped files always have sizes that are mod 4096 which is
        # probably block size.
        #
        # I haven't tested other operating systems.
        block_size = self.get_block_size()

        delta = self.SIZE % block_size

        if delta:
            crude_size = (self.SIZE - delta) + block_size
        else:
            crude_size = self.SIZE

        f = mmap.mmap(self.mem.fd, self.SIZE)

        s = f.read(self.SIZE)

        # I accept both the accurate and crude block size because I don't know
        # which operating system will return which.
        self.assertIn(f.size(), (self.SIZE, crude_size))

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
