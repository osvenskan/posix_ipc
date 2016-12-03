# Python modules
import time

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils


def process_notification(mq):
    message, priority = mq.receive()

    print("Ding! Message with priority %d received: %s" % (priority, message))


# Create the message queue.
mq = posix_ipc.MessageQueue(utils.QUEUE_NAME, posix_ipc.O_CREX)

# Request notifications
mq.request_notification((process_notification, mq))

# Get user input and send it to the queue.
print("Enter a message:")
mq.send(utils.get_input())

# The callback happens almost instantly, but if I don't pause at least
# briefly then the main thread may exit before the notification fires.
print("Sleeping for one second to allow the notification to happen.")
time.sleep(1)

print("Destroying the message queue.")
mq.close()
# I could call simply mq.unlink() here but in order to demonstrate
# unlinking at the module level I'll do it that way.
posix_ipc.unlink_message_queue(utils.QUEUE_NAME)
