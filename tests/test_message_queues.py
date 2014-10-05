# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import datetime
import random
import time
import signal
import threading

# Project imports
import posix_ipc
import base as tests_base

if hasattr(posix_ipc, 'USER_SIGNAL_MIN'):
    SIGNAL_VALUE = posix_ipc.USER_SIGNAL_MIN
else:
    SIGNAL_VALUE = signal.SIGHUP


signal_handler_value_received = 0

def signal_handler(signal_value, frame):
    # FIXME docstring
    global signal_handler_value_received
    signal_handler_value_received = signal_value

def threaded_notification_handler_one_shot(test_case_instance):
    # FIXME docstring
    test_case_instance.threaded_notification_called = True
    test_case_instance.notification_event.set()

def threaded_notification_handler_rearm(test_case_instance):
    # FIXME docstring
    # Rearm.
    param = (threaded_notification_handler_rearm, test_case_instance)
    test_case_instance.mq.request_notification(param)

    test_case_instance.threaded_notification_called = True
    test_case_instance.notification_event.set()


if posix_ipc.MESSAGE_QUEUES_SUPPORTED:
    class TestMessageQueues(tests_base.Base):
        def _test_assign_to_read_only_property(self, property_name, value):
            """test that writing to a readonly property raises TypeError"""
            # Awkward syntax here because I can't use assertRaises in a context
            # manager in Python < 2.7.
            def assign(property_name):
                setattr(self.mq, property_name, value)

            # raises TypeError: readonly attribute
            self.assertRaises(TypeError, assign)

        def setUp(self):
            self.mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)

        def tearDown(self):
            if self.mq:
                self.mq.close()
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

        ###### test send

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

            self.assertRaises(posix_ipc.BusyError, self.mq.send, 'foo',
                              timeout=0)

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

        ###### test receive()

        def test_receive(self):
            """Test that simple receive works.

            It's already tested elsewhere implicitly, but I want an explicit
            test.
            """
            self.mq.send('foo', priority=3)

            self.assertEqual(self.mq.receive(), ('foo'.encode(), 3))

        # FIXME This test fails
        # def test_receive_timeout_keyword(self):
        #     """Test that the timeout keyword of receive works."""
        #     self.assertRaises(posix_ipc.BusyError, self.mq.receive,
        #                       timeout=0)

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

        # FIXME under py3, receive returns bytes

        ###### test request_notification()

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

        # FIXME this fails
        # def test_request_notification_cancel_keyword(self):
        #     """Test that notification can be cancelled with a keyword param"""
        #     global signal_handler_value_received

        #     self.mq.request_notification(SIGNAL_VALUE)

        #     signal.signal(SIGNAL_VALUE, signal_handler)

        #     signal_handler_value_received = 0

        #     # Cancel notification
        #     self.mq.request_notification(notification=None)

        #     self.mq.send('')

        #     self.assertEqual(signal_handler_value_received, 0)

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

                # I have to wait on a shared event to ensure that the notification
                # handler's thread gets a chance to execute before I make my
                # assertion.
                self.notification_event.wait(5)

                self.assertTrue(self.threaded_notification_called)

                self.mq.receive()

                self.notification_event.clear()

    def test_close_and_unlink(self):
        """tests that mq.close() and mq.unlink() work"""
        # sem.close() is hard to test since subsequent use of the semaphore
        # after sem.close() is undefined. All I can think of to do is call it
        # and note that it does not fail. Also, it allows sem.unlink() to
        # tell the OS to delete the semaphore entirely, so it makes sense
        # to test them together,
        self.mq.unlink()
        self.mq.close()
        self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                          self.mq.name)

        # Wipe this out so that self.tearDown() doesn't crash.
        self.mq = None

    def test_property_name(self):
        """exercise MessageQueue.name"""
        self.assertGreaterEqual(len(self.mq.name), 2)

        self.assertEqual(self.mq.name[0], '/')

        self._test_assign_to_read_only_property('name', 'hello world')

    def test_property_mqd(self):
        """exercise MessageQueue.mqd"""
        self.assertNotEqual(self.mq.mqd, -1)

        # The mqd is of type mqd_t. I can't find doc that states what this
        # type is. All I know is that -1 is an error, but I can't tell what
        # else to expect.

        self._test_assign_to_read_only_property('mqd', 42)

    def test_property_max_messages(self):
        """exercise MessageQueue.max_messages"""
        self.assertGreaterEqual(self.mq.max_messages, 0)

        self._test_assign_to_read_only_property('max_messages', 42)

    def test_property_max_message_size(self):
        """exercise MessageQueue.max_message_size"""
        self.assertGreaterEqual(self.mq.max_message_size, 0)

        self._test_assign_to_read_only_property('max_message_size', 42)

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

        self._test_assign_to_read_only_property('current_messages', 42)


    # FIXME need to test block flag




    if __name__ == '__main__':
        unittest.main()
