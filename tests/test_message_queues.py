# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import datetime
import random

# Project imports
import posix_ipc
import base as tests_base


class TestMessageQueues(tests_base.Base):
    def setUp(self):
        self.mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)

    def tearDown(self):
        if self.mq:
            self.mq.unlink()

    def _test_assign_to_read_only_property(self, property_name, value):
        """test that writing to a readonly property raises TypeError"""
        # Awkward syntax here because I can't use assertRaises in a context
        # manager in Python < 2.7.
        def assign(property_name):
            setattr(self.mq, property_name, value)

        # raises TypeError: readonly attribute
        self.assertRaises(TypeError, assign)

    def test_no_flags(self):
        """tests that opening a queue with no flags opens the existing
        queue and doesn't create a new queue"""
        mq_copy = posix_ipc.MessageQueue(self.mq.name)
        self.assertEqual(self.mq.name, mq_copy.name)
        mq_copy.close()

    def test_o_creat_existing(self):
        """tests posix_ipc.O_CREAT to open an existing MessageQueue without
        O_EXCL"""
        mq_copy = posix_ipc.MessageQueue(self.mq.name, posix_ipc.O_CREAT)
        self.assertEqual(self.mq.name, mq_copy.name)
        mq_copy.close()

    def test_o_creat_new(self):
        """tests posix_ipc.O_CREAT to create a new MessageQueue without
        O_EXCL"""
        # I can't pass None for the name unless I also pass O_EXCL.
        name = tests_base.make_name()

        # Note: this method of finding an unused name is vulnerable to a race
        # condition. It's good enough for test, but don't copy it for use in
        # production code!
        name_is_available = False
        while not name_is_available:
            try:
                mq = posix_ipc.MessageQueue(name)
                mq.close()
            except posix_ipc.ExistentialError:
                name_is_available = True
            else:
                name = tests_base.make_name()

        mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREAT)

        self.assertIsNotNone(mq)

        mq.unlink()

    def test_o_excl(self):
        """tests O_CREAT | O_EXCL prevents opening an existing MessageQueue"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                          self.mq.name, posix_ipc.O_CREAT | posix_ipc.O_EXCL)

    def test_o_crex(self):
        """tests O_CREX prevents opening an existing MessageQueue"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                          self.mq.name, posix_ipc.O_CREX)

    def test_randomly_generated_name(self):
        """tests that the randomly-generated name works"""
        # This is tested implicitly elsewhere but I want to test it explicitly
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)
        self.assertIsNotNone(mq.name)

        self.assertEqual(mq.name[0], '/')
        self.assertGreaterEqual(len(mq.name), 2)
        mq.unlink()

    # don't bother testing mode, it's ignored by the OS?

    def test_max_messages(self):
        """test that the max_messages param is respected"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, max_messages=1)

        mq.send('foo')

        self.assertRaises(posix_ipc.BusyError, mq.send, 'bar', timeout=0)

        mq.unlink()

    def test_max_message_size(self):
        """test that the max_message_size param is respected"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, max_message_size=10)

        self.assertRaises(ValueError, mq.send, ' ' * 11)

        mq.unlink()


    # def test_zero_initial_value(self):
    #     """tests that the initial value is 0 when assigned"""
    #     if posix_ipc.MessageQueue_VALUE_SUPPORTED:
    #         sem = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, initial_value=0)
    #         self.assertEqual(mq.value, 0)
    #         mq.unlink()

    # def test_nonzero_initial_value(self):
    #     """tests that the initial value is non-zero when assigned"""
    #     if posix_ipc.MessageQueue_VALUE_SUPPORTED:
    #         sem = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, initial_value=42)
    #         self.assertEqual(mq.value, 42)
    #         mq.unlink()


    # # test sacquisition
    # def test_simple_acquisition(self):
    #     """tests that acquisition works"""
    #     # I should be able to acquire this MessageQueue, but if I can't I don't
    #     # want to hang the test. Acquiring with timeout=0 will raise a BusyError
    #     # if the MessageQueue can't be acquired. That works even when
    #     # MessageQueue_TIMEOUT_SUPPORTED is False.
    #     self.mq.acquire(0)

    # # test acquisition failures
    # # def test_acquisition_no_timeout(self):
    # # This is hard to test since it should wait infinitely. Probably the way
    # # to do it is to spawn another process that holds the MessageQueue for
    # # maybe 10 seconds and have this process wait on it. That's complicated
    # # and not a really great test.

    # def test_acquisition_zero_timeout(self):
    #     """tests that acquisition w/timeout=0 implements non-blocking
    #     behavior"""
    #     # Should not raise an error
    #     self.mq.acquire(0)

    #     # I would prefer this syntax, but it doesn't work with Python < 2.7.
    #     # with self.assertRaises(posix_ipc.BusyError):
    #     #     self.mq.acquire(0)
    #     self.failUnlessRaises(posix_ipc.BusyError, self.mq.acquire, 0)


    # def test_acquisition_nonzero_int_timeout(self):
    #     """tests that acquisition w/timeout=an int is reasonably accurate"""
    #     if posix_ipc.MessageQueue_TIMEOUT_SUPPORTED:
    #         # Should not raise an error
    #         self.mq.acquire(0)

    #         # This should raise a busy error
    #         wait_time = 1
    #         start = datetime.datetime.now()
    #         # I would prefer this syntax, but it doesn't work with Python < 2.7.
    #         # with self.assertRaises(posix_ipc.BusyError):
    #         #     self.mq.acquire(wait_time)
    #         self.failUnlessRaises(posix_ipc.BusyError, self.mq.acquire,
    #                               wait_time)
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
    #     if posix_ipc.MessageQueue_TIMEOUT_SUPPORTED:
    #         # Should not raise an error
    #         self.mq.acquire(0)

    #         # This should raise a busy error
    #         wait_time = 1.5
    #         start = datetime.datetime.now()
    #         # I would prefer this syntax, but it doesn't work with Python < 2.7.
    #         # with self.assertRaises(posix_ipc.BusyError):
    #         #     self.mq.acquire(wait_time)
    #         self.failUnlessRaises(posix_ipc.BusyError, self.mq.acquire,
    #                               wait_time)
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
    #     # Not only does it work, I can do it as many times as I want! I had
    #     # tried some code that called release() MessageQueue_VALUE_MAX times, but
    #     # on platforms where that's ~2 billion, the test takes too long to run.
    #     # So I'll stick to a lower (but still very large) number of releases.
    #     n_releases = min(N_RELEASES, posix_ipc.MessageQueue_VALUE_MAX - 1)
    #     for i in range(n_releases):
    #         self.mq.release()

    # def test_context_manager(self):
    #     """tests that context manager acquire/release works"""
    #     with self.sem as sem:
    #         if posix_ipc.MessageQueue_VALUE_SUPPORTED:
    #             self.assertEqual(mq.value, 0)
    #         # I would prefer this syntax, but it doesn't work with Python < 2.7.
    #         # with self.assertRaises(posix_ipc.BusyError):
    #         #     mq.acquire(0)
    #         self.failUnlessRaises(posix_ipc.BusyError, mq.acquire, 0)

    #     if posix_ipc.MessageQueue_VALUE_SUPPORTED:
    #         self.assertEqual(mq.value, 1)

    #     # Should not raise an error.
    #     mq.acquire(0)

    # def test_close_and_unlink(self):
    #     """tests that mq.close() and mq.unlink() works"""
    #     # mq.close() is hard to test since subsequent use of the MessageQueue
    #     # after mq.close() is undefined. All I can think of to do is call it
    #     # and note that it does not fail. Also, it allows mq.unlink() to
    #     # tell the OS to delete the MessageQueue entirely, so it makes sense
    #     # to test them together,
    #     #self.mq.close()

    #     self.mq.unlink()
    #     self.mq.close()
    #     self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
    #                       self.mq.name)

    #     # Wipe this out so that self.tearDown() doesn't crash.
    #     self.sem = None

    # def test_property_name(self):
    #     """exercise MessageQueue.name"""
    #     self.assertGreaterEqual(len(self.mq.name), 2)

    #     self.assertEqual(self.mq.name[0], '/')

    #     self._test_assign_to_read_only_property('name', 'hello world')

    # def test_property_value(self):
    #     """exercise MessageQueue.value if possible"""
    #     # test read, although this has been tested very thoroughly above
    #     if posix_ipc.MessageQueue_VALUE_SUPPORTED:
    #         self.assertEqual(self.mq.value, 1)

    #         self._test_assign_to_read_only_property('value', 42)




if __name__ == '__main__':
    unittest.main()
