# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import numbers
import platform
import unittest
import mmap
import os
import sys

# Project imports
import posix_ipc
# Hack -- add tests directory to sys.path so Python 3 can find base.py.
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
import base as tests_base  # noqa

_IS_MACOS = "Darwin" in platform.uname()


def _get_block_size():
    """Return block size as reported by operating system"""
    # I thought it would be a good idea to pass self.mem.name to os.statvfs in case that
    # filesystem is different from the regular one, but I get 'No such file or directory'
    # when I do so. This happens on macOS and Linux, didn't test elsewhere.
    return os.statvfs('.')[1]


class TestMemory(tests_base.Base):
    """Exercise the SharedMemory class"""
    # SIZE should be something that's not a power of 2 since that's more
    # likely to expose odd behavior.
    SIZE = 3333

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

    @unittest.skipIf(_IS_MACOS, "O_TRUNC is not supported under macOS")
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
            name = tests_base.make_name().decode('ASCII')
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
        block_size = _get_block_size()

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

    @unittest.skipUnless(sys.stdin.fileno() == 0, "Requires stdin to have file number 0")
    def test_ctor_fd_can_become_zero(self):
        """test that SharedMemory accepts 0 as valid file descriptor"""
        # ref: https://github.com/osvenskan/posix_ipc/issues/2
        # This test relies on OS compliance with the POSIX spec. Specifically, the spec for
        # shm_open() says --
        #
        #     shm_open() shall return a file descriptor for the shared memory
        #     object that is the lowest numbered file descriptor not currently
        #     open for that process.
        #
        # ref: http://pubs.opengroup.org/onlinepubs/009695399/functions/shm_open.html
        #
        # So, on systems compliant with that particular part of the spec, if I open a SharedMemory
        # segment after closing stdin (which has fd == 0), the SharedMemory segment, should be
        # assigned fd 0.
        os.close(0)

        # I have to supply a size here, otherwise the call to close_fd() will fail under macOS.
        # See here for another report of the same behavior:
        # https://stackoverflow.com/questions/35371133/close-on-shared-memory-in-osx-causes-invalid-argument-error
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=4096)
        mem_fd = mem.fd
        # Clean up before attempting the assertion in case the assertion fails.
        mem.close_fd()
        mem.unlink()

        self.assertEqual(mem_fd, 0)

    def test_object_method_close_fd(self):
        """test that SharedMemory.close_fd() closes the file descriptor"""
        mem = posix_ipc.SharedMemory(self.mem.name)

        mem.close_fd()

        self.assertEqual(mem.fd, -1)

        # On at least one platform (my Mac), this raises OSError under Python 2.7 and ValueError
        # under Python 3.6.
        with self.assertRaises((OSError, ValueError)):
            os.fdopen(mem.fd)

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
        self.assertIsInstance(self.mem.fd, numbers.Integral)

        self.assertWriteToReadOnlyPropertyFails('fd', 42)

    def test_fileno(self):
        """exercise SharedMemory.fileno"""
        self.assertEqual(self.mem.fd, self.mem.fileno())

    def test_size_property(self):
        """exercise SharedMemory.size"""
        self.assertIsInstance(self.mem.size, numbers.Integral)

        self.assertWriteToReadOnlyPropertyFails('size', 42)


class TestMemoryResize(tests_base.Base):
    """Exercise various aspects of resizing an existing SharedMemory segment.

    The more interesting aspects of this test don't run under macOS because resizing isn't
    supported on that platform.
    """
    def setUp(self):
        # In constrast to the other memory test that deliberately uses an odd size, this test
        # uses a product of the system's block size. As noted above, the spec doesn't require
        # the segment to exactly respect the specified size. In practice probably all systems
        # respect it as long as it's evenly divisible by the block size.
        # One of the tests in this case attempts to cut the memory size in half, and I want to
        # mitigate the possibility that it will fail due to a platform-specific implementation
        # (e.g. trying to create a segment that's smaller than some arbitrary OS minimum).
        # Creating a segment that's twice the size of the block size seems the best option since
        # dividing it in half still leaves a segment size that's likely to be acceptable on
        # all platforms.
        self.original_size = _get_block_size() * 2
        self.mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=self.original_size)

    def tearDown(self):
        if self.mem:
            self.mem.close_fd()
            self.mem.unlink()

    def test_ctor_second_handle_default_size_no_change(self):
        """opening an existing segment with the default size shouldn't change the size."""
        mem = posix_ipc.SharedMemory(self.mem.name)
        self.assertEqual(mem.size, self.original_size)
        self.assertEqual(self.mem.size, self.original_size)
        mem.close_fd()

    def test_ctor_second_handle_explicit_size_no_change(self):
        """opening an existing segment with an explicit size of 0 shouldn't change the size."""
        mem = posix_ipc.SharedMemory(self.mem.name, size=0)
        self.assertEqual(mem.size, self.original_size)
        self.assertEqual(self.mem.size, self.original_size)
        mem.close_fd()

    @unittest.skipIf(_IS_MACOS, "Changing shared memory size is not supported under macOS")
    def test_ctor_second_handle_size_increase(self):
        """exercise increasing the size of an existing segment via a second handle to it"""
        new_size = self.original_size * 2
        mem = posix_ipc.SharedMemory(self.mem.name, size=new_size)
        self.assertEqual(mem.size, new_size)
        self.assertEqual(self.mem.size, new_size)
        mem.close_fd()

    @unittest.skipIf(_IS_MACOS, "Changing shared memory size is not supported under macOS")
    def test_ctor_second_handle_size_decrease(self):
        """exercise decreasing the size of an existing segment via a second handle to it"""
        new_size = self.original_size // 2
        mem = posix_ipc.SharedMemory(self.mem.name, size=new_size)
        self.assertEqual(mem.size, new_size)
        self.assertEqual(self.mem.size, new_size)
        mem.close_fd()

    def test_ftruncate_increase(self):
        """exercise increasing the size of an existing segment from 0 via ftruncate()"""
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX)
        self.assertEqual(mem.size, 0)
        new_size = _get_block_size()
        os.ftruncate(mem.fd, new_size)
        self.assertEqual(mem.size, new_size)


if __name__ == '__main__':
    unittest.main()
