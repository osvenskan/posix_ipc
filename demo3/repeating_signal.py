# Python modules
import signal

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils


MY_SIGNAL = signal.SIGUSR1


def handle_signal(signal_number, stack_frame):
    message, priority = mq.receive()

    print("Ding! Message with priority %d received: %s" % (priority, message))

    # Re-register for notifications
    mq.request_notification(MY_SIGNAL)


# Create the message queue.
mq = posix_ipc.MessageQueue(utils.QUEUE_NAME, posix_ipc.O_CREX)

# Request notifications
mq.request_notification(MY_SIGNAL)

# Register my signal handler
signal.signal(MY_SIGNAL, handle_signal)

# Get user input and send it to the queue.
msg = "42"
while msg:
    print("\nEnter a message. A blank message will end the demo:")
    msg = utils.get_input()
    if msg:
        mq.send(msg)

print("Destroying the message queue.")
mq.close()
# I could call simply mq.unlink() here but in order to demonstrate
# unlinking at the module level I'll do it that way.
posix_ipc.unlink_message_queue(utils.QUEUE_NAME)
