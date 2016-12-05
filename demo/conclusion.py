# Python modules
import mmap
import os
import sys
import hashlib

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils


PY_MAJOR_VERSION = sys.version_info[0]

utils.say("Oooo 'ello, I'm Mrs. Conclusion!")

params = utils.read_params()

# Mrs. Premise has already created the semaphore and shared memory.
# I just need to get handles to them.
memory = posix_ipc.SharedMemory(params["SHARED_MEMORY_NAME"])
semaphore = posix_ipc.Semaphore(params["SEMAPHORE_NAME"])

# MMap the shared memory
mapfile = mmap.mmap(memory.fd, memory.size)

# Once I've mmapped the file descriptor, I can close it without
# interfering with the mmap. This also demonstrates that os.close() is a
# perfectly legitimate alternative to the SharedMemory's close_fd() method.
os.close(memory.fd)

what_i_wrote = ""

for i in range(0, params["ITERATIONS"]):
    utils.say("iteration %d" % i)
    if not params["LIVE_DANGEROUSLY"]:
        # Wait for Mrs. Premise to free up the semaphore.
        utils.say("Waiting to acquire the semaphore")
        semaphore.acquire()

    s = utils.read_from_memory(mapfile)

    while s == what_i_wrote:
        if not params["LIVE_DANGEROUSLY"]:
            # Release the semaphore...
            utils.say("Releasing the semaphore")
            semaphore.release()
            # ...and wait for it to become available again.
            utils.say("Waiting to acquire the semaphore")
            semaphore.acquire()

        s = utils.read_from_memory(mapfile)

    if what_i_wrote:
        if PY_MAJOR_VERSION > 2:
            what_i_wrote = what_i_wrote.encode()
        try:
            assert(s == hashlib.md5(what_i_wrote).hexdigest())
        except AssertionError:
            utils.raise_error(AssertionError,
                              "Shared memory corruption after %d iterations." % i)

    if PY_MAJOR_VERSION > 2:
        s = s.encode()
    what_i_wrote = hashlib.md5(s).hexdigest()

    utils.write_to_memory(mapfile, what_i_wrote)

    if not params["LIVE_DANGEROUSLY"]:
        utils.say("Releasing the semaphore")
        semaphore.release()

semaphore.close()
mapfile.close()

utils.say("")
utils.say("%d iterations complete" % (i + 1))
