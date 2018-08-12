# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
from unittest import skipUnless
import time
import signal
import threading

# Project imports
import posix_ipc
# Hack -- add tests directory to sys.path so Python 3 can find base.py.
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
import base as tests_base  # noqa

if hasattr(posix_ipc, 'USER_SIGNAL_MIN'):
    # Due to Python bug http://bugs.python.org/issue20584, not all valid signal
    # values can be used. I noticed it on FreeBSD, it might be visible
    # elsewhere.
    if posix_ipc.USER_SIGNAL_MIN >= signal.NSIG:
        SIGNAL_VALUE = signal.SIGHUP
    else:
        SIGNAL_VALUE = posix_ipc.USER_SIGNAL_MIN
else:
    SIGNAL_VALUE = signal.SIGHUP

signal_handler_value_received = 0


def signal_handler(signal_value, frame):
    """Handle signal sent for msg q notification test."""
    global signal_handler_value_received
    signal_handler_value_received = signal_value


def threaded_notification_handler_one_shot(test_case_instance):
    """Handle msg q notification in a thread without rearming notification."""
    test_case_instance.threaded_notification_called = True
    test_case_instance.notification_event.set()


def threaded_notification_handler_rearm(test_case_instance):
    """Handle msg q notification in a thread and rearm notification."""
    # Rearm.
    param = (threaded_notification_handler_rearm, test_case_instance)
    test_case_instance.mq.request_notification(param)

    test_case_instance.threaded_notification_called = True
    test_case_instance.notification_event.set()


class MessageQueueTestBase(tests_base.Base):
    """base class for MessageQueue test classes"""
    def setUp(self):
        self.mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)

    def tearDown(self):
        if self.mq:
            self.mq.close()
            self.mq.unlink()

    def assertWriteToReadOnlyPropertyFails(self, property_name, value):
        """test that writing to a readonly property raises TypeError"""
        tests_base.Base.assertWriteToReadOnlyPropertyFails(self, self.mq, property_name, value)


@skipUnless(posix_ipc.MESSAGE_QUEUES_SUPPORTED, "Requires MessageQueue support")
class TestMessageQueueCreation(MessageQueueTestBase):
    """Exercise stuff related to creating MessageQueue"""
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

        # Note: this method of finding an unused name is vulnerable to a
        # race condition. It's good enough for test, but don't copy it for
        # use in production code!
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
        mq.close()
        mq.unlink()

    def test_o_crex(self):
        """tests O_CREX prevents opening an existing MessageQueue"""
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                          self.mq.name, posix_ipc.O_CREX)

    def test_randomly_generated_name(self):
        """tests that the randomly-generated name works"""
        # This is tested implicitly elsewhere but I want an explicit test
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)
        self.assertIsNotNone(mq.name)

        self.assertEqual(mq.name[0], '/')
        self.assertGreaterEqual(len(mq.name), 2)
        mq.close()
        mq.unlink()

    def test_name_as_bytes(self):
        """Test that the name can be bytes.

        In Python 2, bytes == str. This test is really only interesting in Python 3.
        """
        if tests_base.IS_PY3:
            name = bytes(tests_base.make_name(), 'ASCII')
        else:
            name = bytes(tests_base.make_name())
        mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)
        # No matter what the name is passed as, posix_ipc.name returns the default string type,
        # i.e. str in Python 2 and unicode in Python 3.
        if tests_base.IS_PY3:
            self.assertEqual(name, bytes(mq.name, 'ASCII'))
        else:
            self.assertEqual(name, mq.name)
        mq.unlink()
        mq.close()

    def test_name_as_unicode(self):
        """Test that the name can be unicode.

        In Python 3, str == unicode. This test is really only interesting in Python 2.
        """
        if tests_base.IS_PY3:
            name = tests_base.make_name()
        else:
            name = unicode(tests_base.make_name(), 'ASCII')
        mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)
        self.assertEqual(name, mq.name)
        mq.unlink()
        mq.close()

    # don't bother testing mode, it's ignored by the OS?

    def test_max_messages(self):
        """test that the max_messages param is respected"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, max_messages=1)
        mq.send('foo')
        self.assertRaises(posix_ipc.BusyError, mq.send, 'bar', timeout=0)
        mq.close()
        mq.unlink()

    def test_max_message_size(self):
        """test that the max_message_size param is respected"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX,
                                    max_message_size=10)
        self.assertRaises(ValueError, mq.send, ' ' * 11)
        mq.close()
        mq.unlink()

    def test_read_flag_new_queue(self):
        """test that the read flag is respected on a new queue"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, read=False)
        mq.send('foo')
        self.assertRaises(posix_ipc.PermissionsError, mq.receive)
        mq.close()
        mq.unlink()

    def test_read_flag_existing_queue(self):
        """test that the read flag is respected on an existing queue"""
        mq = posix_ipc.MessageQueue(self.mq.name, read=False)
        mq.send('foo')
        self.assertRaises(posix_ipc.PermissionsError, mq.receive)
        mq.close()

    def test_write_flag_new_queue(self):
        """test that the write flag is respected on a new queue"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, write=False)
        self.assertRaises(posix_ipc.PermissionsError, mq.send, 'foo')
        mq.close()
        mq.unlink()

    def test_write_flag_existing_queue(self):
        """test that the write flag is respected on an existing queue"""
        mq = posix_ipc.MessageQueue(self.mq.name, write=False)
        self.assertRaises(posix_ipc.PermissionsError, mq.send, 'foo')
        mq.close()

    def test_kwargs(self):
        """ensure init accepts keyword args as advertised"""
        # mode 0x180 = 0600. Octal is difficult to express in Python 2/3 compatible code.
        mq = posix_ipc.MessageQueue(None, flags=posix_ipc.O_CREX, mode=0x180, max_messages=1,
                                    max_message_size=256, read=True, write=True)
        mq.close()
        mq.unlink()


@skipUnless(posix_ipc.MESSAGE_QUEUES_SUPPORTED, "Requires MessageQueue support")
class TestMessageQueueSendReceive(MessageQueueTestBase):
    """Exercise send() and receive()"""
    def test_send(self):
        """Test that simple send works.

        It's already tested elsewhere implicitly, but I want an explicit
        test.
        """
        self.mq.send('foo')

    # FIXME how to test that send with timeout=None waits as expected?

    def test_send_timeout_keyword(self):
        """Test that the timeout keyword of send works"""
        n_msgs = self.mq.max_messages
        while n_msgs:
            self.mq.send(' ')
            n_msgs -= 1

        self.assertRaises(posix_ipc.BusyError, self.mq.send, 'foo', timeout=0)

    def test_send_timeout_positional(self):
        """Test that the timeout positional param of send works"""
        n_msgs = self.mq.max_messages
        while n_msgs:
            self.mq.send(' ')
            n_msgs -= 1

        self.assertRaises(posix_ipc.BusyError, self.mq.send, 'foo', 0)

    def test_send_timeout_zero_success(self):
        """Test that send w/a timeout=0 succeeds if queue is not full."""
        self.mq.send('foo', timeout=0)

    def test_send_timeout_zero_fails(self):
        """Test that send w/a timeout=0 raises BusyError if queue is
        full.
        """
        n_msgs = self.mq.max_messages
        while n_msgs:
            self.mq.send(' ')
            n_msgs -= 1

        self.assertRaises(posix_ipc.BusyError, self.mq.send, 'foo',
                          timeout=0)

    def test_send_nonzero_timeout(self):
        """Test that a non-zero timeout to send is respected."""
        n_msgs = self.mq.max_messages
        while n_msgs:
            self.mq.send(' ')
            n_msgs -= 1

        start = time.time()
        self.assertRaises(posix_ipc.BusyError, self.mq.send, ' ',
                          timeout=1.0)
        elapsed = time.time() - start
        # I don't insist on extreme precision.
        self.assertTrue(elapsed >= 1.0)
        self.assertTrue(elapsed < 1.5)

    def test_send_priority_default(self):
        """Test that the send priority defaults to 0"""
        self.mq.send('foo')
        self.assertEqual(self.mq.receive(), ('foo'.encode(), 0))

    def test_send_fifo_default(self):
        """Test that the queue order is FIFO by default"""
        alphabet = 'abcdefg'
        for c in alphabet:
            self.mq.send(c)

        for c in alphabet:
            self.assertEqual(self.mq.receive(), (c.encode(), 0))

    def test_send_priority(self):
        """Test that the priority param is respected"""
        # By simple FIFO, these would be returned lowest, highest, middle.
        # Instead they'll be returned highest, middle, lowest
        self.mq.send('lowest', priority=1)
        self.mq.send('highest', priority=3)
        self.mq.send('middle', priority=2)

        self.assertEqual(self.mq.receive(), ('highest'.encode(), 3))
        self.assertEqual(self.mq.receive(), ('middle'.encode(), 2))
        self.assertEqual(self.mq.receive(), ('lowest'.encode(), 1))

    def test_send_priority_keyword(self):
        """Test that the priority keyword of send works"""
        self.mq.send('foo', priority=42)
        self.assertEqual(self.mq.receive(), ('foo'.encode(), 42))

    def test_send_priority_positional(self):
        """Test that the priority positional param of send works"""
        self.mq.send('foo', 0, 42)
        self.assertEqual(self.mq.receive(), ('foo'.encode(), 42))

    def test_send_kwargs(self):
        """ensure send() accepts keyword args as advertised"""
        self.mq.send('foo', timeout=0, priority=0)

    # ##### test receive()

    def test_receive(self):
        """Test that simple receive works.

        It's already tested elsewhere implicitly, but I want an explicit
        test.
        """
        self.mq.send('foo', priority=3)

        self.assertEqual(self.mq.receive(), ('foo'.encode(), 3))

    def test_receive_timeout_positional(self):
        """Test that the timeout positional param of receive works."""
        self.assertRaises(posix_ipc.BusyError, self.mq.receive, 0)

    def test_receive_nonzero_timeout(self):
        """Test that a non-zero timeout to receive is respected."""
        start = time.time()
        self.assertRaises(posix_ipc.BusyError, self.mq.receive, 1.0)
        elapsed = time.time() - start
        # I don't insist on extreme precision.
        self.assertTrue(elapsed >= 1.0)
        self.assertTrue(elapsed < 1.5)

    # FIXME how to test that timeout=None waits forever?


@skipUnless(posix_ipc.MESSAGE_QUEUES_SUPPORTED, "Requires MessageQueue support")
class TestMessageQueueNotification(MessageQueueTestBase):
    """exercise request_notification()"""
    def test_request_notification_signal(self):
        """Exercise notification by signal"""
        global someone_rang_the_doorbell

        self.mq.request_notification(SIGNAL_VALUE)

        signal.signal(SIGNAL_VALUE, signal_handler)

        someone_rang_the_doorbell = False

        self.mq.send('')

        self.assertEqual(signal_handler_value_received, SIGNAL_VALUE)

    def test_request_notification_signal_one_shot(self):
        """Test that after notification by signal, notification is
        cancelled"""
        global signal_handler_value_received

        self.mq.request_notification(SIGNAL_VALUE)

        signal.signal(SIGNAL_VALUE, signal_handler)

        signal_handler_value_received = 0

        self.mq.send('')

        self.assertEqual(signal_handler_value_received, SIGNAL_VALUE)

        # Reset the global flag
        signal_handler_value_received = 0

        self.mq.send('')

        # Flag should not be set because it's only supposed to fire
        # notification when the queue changes from empty to non-empty,
        # and there was already 1 msg in the Q when I called send() above.
        self.assertEqual(signal_handler_value_received, 0)

        # empty the queue
        self.mq.receive()
        self.mq.receive()

        self.assertEqual(signal_handler_value_received, 0)

        self.mq.send('')

        # Flag should still not be set because notification was cancelled
        # after it fired the first time.
        self.assertEqual(signal_handler_value_received, 0)

    def test_request_notification_cancel_default(self):
        """Test that notification can be cancelled with the default param"""
        global signal_handler_value_received

        self.mq.request_notification(SIGNAL_VALUE)

        signal.signal(SIGNAL_VALUE, signal_handler)

        signal_handler_value_received = 0

        # Cancel notification
        self.mq.request_notification()

        self.mq.send('')

        self.assertEqual(signal_handler_value_received, 0)

    def test_request_notification_cancel_multiple(self):
        """Test that notification can be cancelled multiple times"""
        self.mq.request_notification(SIGNAL_VALUE)

        # Cancel notification lots of times
        for i in range(1000):
            self.mq.request_notification()

    def test_request_notification_threaded_one_shot(self):
        """Test simple threaded notification"""

        self.threaded_notification_called = False

        param = (threaded_notification_handler_one_shot, self)
        self.mq.request_notification(param)

        self.notification_event = threading.Event()

        self.mq.send('')

        # I have to wait on a shared event to ensure that the notification
        # handler's thread gets a chance to execute before I make my
        # assertion.
        self.notification_event.wait(5)

        self.assertTrue(self.threaded_notification_called)

    def test_request_notification_threaded_rearm(self):
        """Test threaded notification in which the notified thread rearms
        the notification"""

        self.threaded_notification_called = False

        param = (threaded_notification_handler_rearm, self)
        self.mq.request_notification(param)

        self.notification_event = threading.Event()

        # Re-arm several times.
        for i in range(10):
            self.mq.send('')

            # I have to wait on a shared event to ensure that the
            # notification handler's thread gets a chance to execute before
            # I make my assertion.
            self.notification_event.wait(5)

            self.assertTrue(self.threaded_notification_called)

            self.mq.receive()

            self.notification_event.clear()


@skipUnless(posix_ipc.MESSAGE_QUEUES_SUPPORTED, "Requires MessageQueue support")
class TestMessageQueueDestruction(MessageQueueTestBase):
    """exercise close() and unlink()"""

    def test_close_and_unlink(self):
        """tests that mq.close() and mq.unlink() work"""
        # mq.close() is hard to test since subsequent use of the queue
        # after mq.close() is undefined. All I can think of to do is call it
        # and note that it does not fail. Also, it allows mq.unlink() to
        # tell the OS to delete the queue entirely, so it makes sense
        # to test them together,
        self.mq.unlink()
        self.mq.close()
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                          self.mq.name)

        # Wipe this out so that self.tearDown() doesn't crash.
        self.mq = None


@skipUnless(posix_ipc.MESSAGE_QUEUES_SUPPORTED, "Requires MessageQueue support")
class TestMessageQueuePropertiesAndAttributes(MessageQueueTestBase):
    """Exercise props and attrs"""
    def test_property_name(self):
        """exercise MessageQueue.name"""
        self.assertGreaterEqual(len(self.mq.name), 2)

        self.assertEqual(self.mq.name[0], '/')

        self.assertWriteToReadOnlyPropertyFails('name', 'hello world')

    def test_property_mqd(self):
        """exercise MessageQueue.mqd"""
        self.assertNotEqual(self.mq.mqd, -1)

        # The mqd is of type mqd_t. I can't find doc that states what this
        # type is. All I know is that -1 is an error so it's probably
        # int-ish, but I can't tell exactly what to expect.
        self.assertWriteToReadOnlyPropertyFails('mqd', 42)

    def test_fileno(self):
        """exercise MessageQueue.fileno()"""
        self.assertEqual(self.mq.mqd, self.mq.fileno())

    def test_property_max_messages(self):
        """exercise MessageQueue.max_messages"""
        self.assertGreaterEqual(self.mq.max_messages, 0)

        self.assertWriteToReadOnlyPropertyFails('max_messages', 42)

    def test_property_max_message_size(self):
        """exercise MessageQueue.max_message_size"""
        self.assertGreaterEqual(self.mq.max_message_size, 0)

        self.assertWriteToReadOnlyPropertyFails('max_message_size', 42)

    def test_property_current_messages(self):
        """exercise MessageQueue.current_messages"""
        self.assertEqual(self.mq.current_messages, 0)

        self.mq.send('')
        self.assertEqual(self.mq.current_messages, 1)
        self.mq.send('')
        self.mq.send('')
        self.mq.send('')
        self.assertEqual(self.mq.current_messages, 4)
        self.mq.receive()
        self.assertEqual(self.mq.current_messages, 3)
        self.mq.receive()
        self.assertEqual(self.mq.current_messages, 2)
        self.mq.receive()
        self.assertEqual(self.mq.current_messages, 1)
        self.mq.receive()
        self.assertEqual(self.mq.current_messages, 0)

        self.assertWriteToReadOnlyPropertyFails('current_messages', 42)

    def test_block_flag_default_value_and_writability(self):
        """test that the block flag is True by default and can be changed"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)

        self.assertTrue(mq.block)

        # Toggle. I expect no errors. It's good to test this on a queue
        # that's only used for this particular test. I would rather have
        # all the other tests execute using the default value of block
        # on self.mq.
        mq.block = False
        mq.block = True

        mq.close()
        mq.unlink()

    def test_block_flag_false(self):
        """test blocking behavior when flag is false"""
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX, max_messages=3)

        mq.block = False

        # Queue is empty, so receive() should immediately raise BusyError
        start = time.time()
        self.assertRaises(posix_ipc.BusyError, mq.receive, 10)
        elapsed = time.time() - start

        # Not only should receive() have raised BusyError, it should have
        # done so "immediately". I don't insist on extreme precision since
        # OS-level task switching might mean that elapsed time is not
        # vanishingly small as one might expect under most circumstances.
        self.assertTrue(elapsed < 1.0)

        # Now test send() the same way.
        mq.send(' ')
        mq.send(' ')
        mq.send(' ')

        # Queue is now full.
        start = time.time()
        self.assertRaises(posix_ipc.BusyError, mq.send, ' ', 10)
        elapsed = time.time() - start
        self.assertTrue(elapsed < 1.0)

        mq.close()
        mq.unlink()


if __name__ == '__main__':
    unittest.main()
