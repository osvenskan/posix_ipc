# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import os
import resource

# Project imports
import posix_ipc
# Hack -- add tests directory to sys.path so Python 3 can find base.py.
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
import base as tests_base  # noqa

ONE_MILLION = 1000000


class TestModule(tests_base.Base):
    """Exercise the posix_ipc module-level functions and constants"""
    def test_constant_values(self):
        """test that constants are what I expect"""
        self.assertEqual(posix_ipc.O_CREAT, os.O_CREAT)
        self.assertEqual(posix_ipc.O_EXCL, os.O_EXCL)
        self.assertEqual(posix_ipc.O_CREX, posix_ipc.O_CREAT | posix_ipc.O_EXCL)
        self.assertEqual(posix_ipc.O_TRUNC, os.O_TRUNC)

        self.assertEqual(posix_ipc.PAGE_SIZE, resource.getpagesize())

        self.assertIn(posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED, (True, False))
        self.assertIn(posix_ipc.SEMAPHORE_VALUE_SUPPORTED, (True, False))

        self.assertGreaterEqual(posix_ipc.SEMAPHORE_VALUE_MAX, 1)

        self.assertIn(posix_ipc.MESSAGE_QUEUES_SUPPORTED, (True, False))

        if posix_ipc.MESSAGE_QUEUES_SUPPORTED:
            self.assertGreaterEqual(posix_ipc.QUEUE_MESSAGES_MAX_DEFAULT, 1)
            self.assertGreaterEqual(posix_ipc.QUEUE_MESSAGE_SIZE_MAX_DEFAULT, 1)
            self.assertGreaterEqual(posix_ipc.QUEUE_PRIORITY_MAX, 0)

        if hasattr(posix_ipc, 'USER_SIGNAL_MIN'):
            self.assertGreaterEqual(posix_ipc.USER_SIGNAL_MIN, 1)
        if hasattr(posix_ipc, 'USER_SIGNAL_MAX'):
            self.assertGreaterEqual(posix_ipc.USER_SIGNAL_MAX, 1)

        self.assertTrue(isinstance(posix_ipc.VERSION, str))

    def test_unlink_semaphore(self):
        """Exercise unlink_semaphore"""
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX)
        posix_ipc.unlink_semaphore(sem.name)
        sem.close()
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.Semaphore,
                          sem.name)

    def test_unlink_shared_memory(self):
        """Exercise unlink_shared_memory"""
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=1024)
        mem.close_fd()
        posix_ipc.unlink_shared_memory(mem.name)
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.SharedMemory,
                          mem.name)

    if posix_ipc.MESSAGE_QUEUES_SUPPORTED:
        def test_unlink_message_queue(self):
            """Exercise unlink_message_queue"""
            mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)
            posix_ipc.unlink_message_queue(mq.name)
            mq.close()
            self.assertRaises(posix_ipc.ExistentialError,
                              posix_ipc.MessageQueue, mq.name)

        def test_constant_queue_priority_max(self):
            """Test that QUEUE_PRIORITY_MAX is reported correctly"""
            mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)

            if posix_ipc.QUEUE_PRIORITY_MAX < ONE_MILLION:
                for sent_priority in range(posix_ipc.QUEUE_PRIORITY_MAX + 1):
                    mq.send('', priority=sent_priority)
                    msg, received_priority = mq.receive()
                    self.assertEqual(sent_priority, received_priority)
            # else:
                # QUEUE_PRIORITY_MAX is probably LONG_MAX or larger and
                # testing every value will take too long.

            self.assertRaises(ValueError, mq.send, '',
                              priority=posix_ipc.QUEUE_PRIORITY_MAX + 1)

            mq.unlink()
            mq.close()

    def test_errors(self):
        self.assertTrue(issubclass(posix_ipc.Error, Exception))
        self.assertTrue(issubclass(posix_ipc.SignalError, posix_ipc.Error))
        self.assertTrue(issubclass(posix_ipc.PermissionsError, posix_ipc.Error))
        self.assertTrue(issubclass(posix_ipc.ExistentialError, posix_ipc.Error))
        self.assertTrue(issubclass(posix_ipc.BusyError, posix_ipc.Error))


if __name__ == '__main__':
    unittest.main()
