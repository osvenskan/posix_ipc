# Python modules
import time
import sys
import hashlib

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils

PY_MAJOR_VERSION = sys.version_info[0]

utils.say("Oooo 'ello, I'm Mrs. Premise!")

params = utils.read_params()

# Create the message queue.
mq = posix_ipc.MessageQueue(params["MESSAGE_QUEUE_NAME"], posix_ipc.O_CREX)

# The first message is a random string (the current time).
s = time.asctime()
utils.say("Sending %s" % s)
mq.send(s)
what_i_sent = s

for i in range(0, params["ITERATIONS"]):
    utils.say("iteration %d" % i)

    s, _ = mq.receive()
    s = s.decode()
    utils.say("Received %s" % s)

    # If the message is what I wrote, put it back on the queue.
    while s == what_i_sent:
        # Nothing new; give Mrs. Conclusion another chance to respond.
        mq.send(s)

        s, _ = mq.receive()
        s = s.decode()
        utils.say("Received %s" % s)

    # What I read must be the md5 of what I wrote or something's
    # gone wrong.
    if PY_MAJOR_VERSION > 2:
        what_i_sent = what_i_sent.encode()

    try:
        assert(s == hashlib.md5(what_i_sent).hexdigest())
    except AssertionError:
        utils.raise_error(AssertionError,
                          "Message corruption after %d iterations." % i)

    # MD5 the reply and write back to Mrs. Conclusion.
    s = hashlib.md5(s.encode()).hexdigest()
    utils.say("Sending %s" % s)
    mq.send(s)
    what_i_sent = s

utils.say("")
utils.say("%d iterations complete" % (i + 1))

utils.say("Destroying the message queue.")
mq.close()
# I could call simply mq.unlink() here but in order to demonstrate
# unlinking at the module level I'll do it that way.
posix_ipc.unlink_message_queue(params["MESSAGE_QUEUE_NAME"])
