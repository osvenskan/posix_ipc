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

    def _test_assign_to_read_only_property(self, property_name, value):
        """test that writing to a readonly property raises TypeError"""
        # Awkward syntax here because I can't use assertRaises in a context
        # manager in Python < 2.7.
        def assign(property_name):
            setattr(self.mem, property_name, value)

        # raises TypeError: readonly attribute
        self.assertRaises(TypeError, assign)

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
        """test that the size specified is (somewhat) respected by mmap()"""
        # In limited testing, Linux respects the exact size specified in the
        # SharedMemory() ctor when creating the mmapped file.
        # e.g. when self.SIZE = 3333, the
        # mmapped file is also 3333 bytes.
        #
        # OS X's mmapped files always have sizes that are mod 4096 which is
        # probably block size.
        #
        # I haven't tested other operating systems.
        #
        # This code accepts either value as correct.
        block_size = self.get_block_size()

        delta = self.SIZE % block_size

        if delta:
            # Round up to nearest block size
            crude_size = (self.SIZE - delta) + block_size
        else:
            crude_size = self.SIZE

        # I accept both the accurate and crude block size because I don't know
        # which operating system will return which.
        self.assertIn(self.mem.size, (self.SIZE, crude_size))

        f = mmap.mmap(self.mem.fd, self.SIZE)

        s = f.read(self.SIZE)

        # I accept both the accurate and crude block size because I don't know
        # which operating system will return which.
        self.assertIn(f.size(), (self.SIZE, crude_size))

        f.close()

    def test_read_only_ctor_flag(self):
        """test that specifying the readonly flag prevents writing"""
        mem = posix_ipc.SharedMemory(self.mem.name, read_only=True)
        f = mmap.mmap(mem.fd, self.mem.size, prot=mmap.PROT_READ)
        self.assertRaises(TypeError, f.write, 'hello world')
        mem.close_fd()

    def test_object_method_close_fd(self):
        """test that SharedMemory.close_fd() closes the file descriptor"""
        mem = posix_ipc.SharedMemory(self.mem.name)

        mem.close_fd()

        self.assertRaises(OSError, os.fdopen, mem.fd)

    def test_object_method_close_fd(self):
        """test that SharedMemory.close_fd() closes the file descriptor"""
        mem = posix_ipc.SharedMemory(self.mem.name)

        mem.close_fd()

        self.assertRaises(OSError, os.fdopen, mem.fd)

    def test_unlink(self):
        """test that SharedMemory.unlink() deletes the segment"""
        self.mem.close_fd()
        self.mem.unlink()
        self.assertRaises(posix_ipc.ExistentialError, getattr,
                          self.mem, 'size')
        self.mem = None

    def test_name_property(self):
        """exercise SharedMemory.name"""
        self.assertGreaterEqual(len(self.mem.name), 2)

        self.assertEqual(self.mem.name[0], '/')

        self._test_assign_to_read_only_property('name', 'hello world')

    def test_fd_property(self):
        """exercise SharedMemory.fd"""
        self.assertIsInstance(self.mem.fd, (int, long))

        self._test_assign_to_read_only_property('fd', 42)

    def test_size_property(self):
        """exercise SharedMemory.fd"""
        self.assertIsInstance(self.mem.size, (int, long))

        self._test_assign_to_read_only_property('size', 42)


if __name__ == '__main__':
    unittest.main()
