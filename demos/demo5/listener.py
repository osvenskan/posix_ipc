import posix_ipc
import selectors

# This program uses `posix_ipc` together with the `selectors`library from the
# Python standard library. `selectors` provides "high-level I/O multiplexing" akin to having an
# event library.

# The message queue is created as usual
mq = posix_ipc.MessageQueue("/python_ipc_test", flags=posix_ipc.O_CREAT)
mq.block = False

# Function is defined to handle events on the queue

def accept(message_queue, mask):
    (msg, prio) = message_queue.receive()
    print("Message: ", msg)
    print("Priority: ", prio)

# The selector can now be created...

sel = selectors.DefaultSelector()

# ... and the message queue is registered. Other event sources could also be
# registered simultaneously, but for now we stick to the queue

sel.register(mq, selectors.EVENT_READ, accept)

# `.select()` will block until an event is triggered

print("Listening...")

events = sel.select()
for key, mask in events:
    # `.data` contains the third argument from `.register` above -- we use it for the callback.
    callback = key.data
    callback(key.fileobj, mask)

# With the message successfully received, we can unlink and close.

mq.unlink()
mq.close()
