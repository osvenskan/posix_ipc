# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import platform
import unittest
import datetime
import mmap
import os


# Project imports
import posix_ipc
# Hack -- add tests directory to sys.path so Python 3 can find base.py.
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
import base as tests_base

class TestMemory(tests_base.Base):
    """Exercise the SharedMemory class"""
    # SIZE should be something that's not a power of 2 since that's more
    # likely to expose odd behavior.
    SIZE = 3333

    def get_block_size(self):
        """Return block size as reported by operating system"""
        # I thought it would be a good idea to pass self.mem.name to
        # os.statvfs in case that filesystem is different from the
        # regular one, but I get 'No such file or directory' when I do so.
        # This happens on OS X and Linux, didn't test elsewhere.
        return os.statvfs('.')[1]

    def setUp(self):
        self.mem = posix_ipc.SharedMemory('/foo', posix_ipc.O_CREX,
                                          size=self.SIZE)

    def tearDown(self):
        if self.mem:
            self.mem.close_fd()
            self.mem.unlink()

    def assertWriteToReadOnlyPropertyFails(self, property_name, value):
        """test that writing to a readonly property raises TypeError"""
        tests_base.Base.assertWriteToReadOnlyPropertyFails(self, self.mem,
                                                           property_name, value)

    def test_ctor_no_flags_existing(self):
        """tests that opening a memory segment with no flags opens the existing
        memory and doesn't create a new segment"""
        mem_copy = posix_ipc.SharedMemory('/foo')
        self.assertEqual(self.mem.name, mem_copy.name)

    def test_ctor_no_flags_non_existent(self):
        """test that attempting to open a non-existent memory segment with no
        flags fails"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          '/fjksfjkhsdakh')

    def test_ctor_o_creat_existing(self):
        """tests posix_ipc.O_CREAT to open an existing segment without O_EXCL"""
        mem_copy = posix_ipc.SharedMemory(self.mem.name, posix_ipc.O_CREAT)

        self.assertEqual(self.mem.name, mem_copy.name)

    def test_o_creat_new(self):
        """tests posix_ipc.O_CREAT to create a new mem segment without O_EXCL"""
        mem = posix_ipc.SharedMemory('/lsdhfkjahdskjf', posix_ipc.O_CREAT,
                                     size=4096)
        self.assertIsNotNone(mem)
        mem.close_fd()
        mem.unlink()

    def test_o_excl(self):
        """tests O_CREAT | O_EXCL prevents opening an existing memory segment"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          '/foo', posix_ipc.O_CREAT | posix_ipc.O_EXCL)

    def test_o_crex(self):
        """tests O_CREX prevents opening an existing memory segment"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          '/foo', posix_ipc.O_CREX)

    @unittest.skipIf("Darwin" in platform.uname(), "O_TRUNC is not supported under OS X")
    def test_o_trunc(self):
        """Test that O_TRUNC truncates the memory to 0 bytes"""
        mem_copy = posix_ipc.SharedMemory(self.mem.name, posix_ipc.O_TRUNC)

        self.assertEqual(mem_copy.size, 0)

    def test_randomly_generated_name(self):
        """tests that the randomly-generated name works"""
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=1024)
        self.assertIsNotNone(mem.name)
        self.assertEqual(mem.name[0], '/')
        self.assertGreaterEqual(len(mem.name), 2)
        mem.close_fd()
        mem.unlink()

    def test_name_as_bytes(self):
        """Test that the name can be bytes.

        In Python 2, bytes == str. This test is really only interesting in Python 3.
        """
        if tests_base.IS_PY3:
            name = bytes(tests_base.make_name(), 'ASCII')
        else:
            name = bytes(tests_base.make_name())
        mem = posix_ipc.SharedMemory(name, posix_ipc.O_CREX, size=4096)
        # No matter what the name is passed as, posix_ipc.name returns the default string type,
        # i.e. str in Python 2 and unicode in Python 3.
        if tests_base.IS_PY3:
            self.assertEqual(name, bytes(mem.name, 'ASCII'))
        else:
            self.assertEqual(name, mem.name)
        mem.close_fd()
        mem.unlink()

    def test_name_as_unicode(self):
        """Test that the name can be unicode.

        In Python 3, str == unicode. This test is really only interesting in Python 2.
        """
        if tests_base.IS_PY3:
            name = tests_base.make_name()
        else:
            name = unicode(tests_base.make_name(), 'ASCII')
        mem = posix_ipc.SharedMemory(name, posix_ipc.O_CREX, size=4096)
        self.assertEqual(name, mem.name)
        mem.close_fd()
        mem.unlink()

    # # don't bother testing mode, it's ignored by the OS?

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
        # AFAICT the specification doesn't demand that the size has to match
        # exactly, so this code accepts either value as correct.
        block_size = self.get_block_size()

        delta = self.SIZE % block_size

        if delta:
            # Round up to nearest block size
            crude_size = (self.SIZE - delta) + block_size
        else:
            crude_size = self.SIZE

        self.assertIn(self.mem.size, (self.SIZE, crude_size))

        f = mmap.mmap(self.mem.fd, self.SIZE)

        self.assertIn(f.size(), (self.SIZE, crude_size))

        f.close()

    def test_ctor_read_only_flag(self):
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

    def test_unlink(self):
        """test that SharedMemory.unlink() deletes the segment"""
        name = self.mem.name
        self.mem.close_fd()
        self.mem.unlink()
        self.assertRaises(posix_ipc.ExistentialError, getattr,
                          self.mem, 'size')
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          name)
        self.mem = None

    def test_name_property(self):
        """exercise SharedMemory.name"""
        self.assertGreaterEqual(len(self.mem.name), 2)

        self.assertEqual(self.mem.name[0], '/')

        self.assertWriteToReadOnlyPropertyFails('name', 'hello world')

    def test_fd_property(self):
        """exercise SharedMemory.fd"""
        if tests_base.IS_PY3:
            self.assertIsInstance(self.mem.fd, int)
        else:
            self.assertIsInstance(self.mem.fd, (int, long))

        self.assertWriteToReadOnlyPropertyFails('fd', 42)

    def test_size_property(self):
        """exercise SharedMemory.size"""
        if tests_base.IS_PY3:
            self.assertIsInstance(self.mem.size, int)
        else:
            self.assertIsInstance(self.mem.size, (int, long))

        self.assertWriteToReadOnlyPropertyFails('size', 42)

if __name__ == '__main__':
    unittest.main()
