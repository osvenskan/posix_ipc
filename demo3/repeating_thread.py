# Python modules

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils


def process_notification(mq):
    message, priority = mq.receive()

    print("Ding! Message with priority %d received: %s" % (priority, message))

    # Re-register for notifications
    mq.request_notification((process_notification, mq))


# Create the message queue.
mq = posix_ipc.MessageQueue(utils.QUEUE_NAME, posix_ipc.O_CREX)

# Request notifications
mq.request_notification((process_notification, mq))

# Get user input and send it to the queue.
s = "42"
while s:
    print("\nEnter a message. A blank message will end the demo:")
    s = utils.get_input()
    if s:
        mq.send(s)

print("Destroying the message queue.")
mq.close()
# I could call simply mq.unlink() here but in order to demonstrate
# unlinking at the module level I'll do it that way.
posix_ipc.unlink_message_queue(utils.QUEUE_NAME)
