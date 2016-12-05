# Python modules
import sys
import hashlib

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils

PY_MAJOR_VERSION = sys.version_info[0]

utils.say("Oooo 'ello, I'm Mrs. Conclusion!")

params = utils.read_params()

# Mrs. Premise has already created the message queue. I just need a handle
# to it.
mq = posix_ipc.MessageQueue(params["MESSAGE_QUEUE_NAME"])

what_i_sent = ""

for i in range(0, params["ITERATIONS"]):
    utils.say("iteration %d" % i)

    s, _ = mq.receive()
    s = s.decode()
    utils.say("Received %s" % s)

    while s == what_i_sent:
        # Nothing new; give Mrs. Premise another chance to respond.
        mq.send(s)

        s, _ = mq.receive()
        s = s.decode()
        utils.say("Received %s" % s)

    if what_i_sent:
        if PY_MAJOR_VERSION > 2:
            what_i_sent = what_i_sent.encode()
        try:
            assert(s == hashlib.md5(what_i_sent).hexdigest())
        except AssertionError:
            utils.raise_error(AssertionError,
                              "Message corruption after %d iterations." % i)
    # else:
        # When what_i_sent is blank, this is the first message which
        # I always accept without question.

    # MD5 the reply and write back to Mrs. Premise.
    s = hashlib.md5(s.encode()).hexdigest()
    utils.say("Sending %s" % s)
    mq.send(s)
    what_i_sent = s


utils.say("")
utils.say("%d iterations complete" % (i + 1))
