# Python imports
# Don't add any from __future__ imports here. This code should execute
# against standard Python.
import unittest
import datetime
import random
import time

# Project imports
import posix_ipc
import base as tests_base

ONE_HALF_SECOND = datetime.timedelta(milliseconds=500)

if posix_ipc.MESSAGE_QUEUES_SUPPORTED:
    class TestMessageQueues(tests_base.Base):
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

        def test_o_excl(self):
            """tests O_CREAT | O_EXCL prevents opening an existing
            MessageQueue
            """
            self.assertRaises(posix_ipc.ExistentialError, posix_ipc.MessageQueue,
                              self.mq.name, posix_ipc.O_CREAT | posix_ipc.O_EXCL)

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
            self.assertEqual(self.mq.receive(), ('foo', 0))

        def test_send_fifo_default(self):
            """Test that the queue order is FIFO by default"""
            alphabet = 'abcdefg'
            for c in alphabet:
                self.mq.send(c)

            for c in alphabet:
                self.assertEqual(self.mq.receive(), (c, 0))

        def test_send_priority(self):
            """Test that the priority param is respected"""
            # By simple FIFO, these would be returned lowest, highest, middle.
            # Instead they'll be returned highest, middle, lowest
            self.mq.send('lowest', priority=1)
            self.mq.send('highest', priority=3)
            self.mq.send('middle', priority=2)

            self.assertEqual(self.mq.receive(), ('highest', 3))
            self.assertEqual(self.mq.receive(), ('middle', 2))
            self.assertEqual(self.mq.receive(), ('lowest', 1))

        def test_send_priority_keyword(self):
            """Test that the priority keyword of send works"""
            self.mq.send('foo', priority=42)
            self.assertEqual(self.mq.receive(), ('foo', 42))

        def test_send_priority_positional(self):
            """Test that the priority positional param of send works"""
            self.mq.send('foo', 0, 42)
            self.assertEqual(self.mq.receive(), ('foo', 42))

        ###### test receive()

        def test_receive(self):
            """Test that simple receive works.

            It's already tested elsewhere implicitly, but I want an explicit
            test.
            """
            self.mq.send('foo', priority=3)

            self.assertEqual(self.mq.receive(), ('foo', 3))

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


    if __name__ == '__main__':
        unittest.main()
