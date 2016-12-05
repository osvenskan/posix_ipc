# Python modules
import time
import mmap
import sys
import hashlib

# 3rd party modules
import posix_ipc

# Utils for this demo
import utils

PY_MAJOR_VERSION = sys.version_info[0]

utils.say("Oooo 'ello, I'm Mrs. Premise!")

params = utils.read_params()

# Create the shared memory and the semaphore.
memory = posix_ipc.SharedMemory(params["SHARED_MEMORY_NAME"], posix_ipc.O_CREX,
                                size=params["SHM_SIZE"])
semaphore = posix_ipc.Semaphore(params["SEMAPHORE_NAME"], posix_ipc.O_CREX)

# MMap the shared memory
mapfile = mmap.mmap(memory.fd, memory.size)

# Once I've mmapped the file descriptor, I can close it without
# interfering with the mmap.
memory.close_fd()

# I seed the shared memory with a random string (the current time).
what_i_wrote = time.asctime()
utils.write_to_memory(mapfile, what_i_wrote)

for i in range(params["ITERATIONS"]):
    utils.say("iteration %d" % i)
    if not params["LIVE_DANGEROUSLY"]:
        # Release the semaphore...
        utils.say("Releasing the semaphore")
        semaphore.release()
        # ...and wait for it to become available again. In real code
        # I might want to sleep briefly before calling .acquire() in
        # order to politely give other processes an opportunity to grab
        # the semaphore while it is free so as to avoid starvation. But
        # this code is meant to be a stress test that maximizes the
        # opportunity for shared memory corruption and politeness is
        # not helpful in stress tests.
        utils.say("Waiting to acquire the semaphore")
        semaphore.acquire()

    s = utils.read_from_memory(mapfile)

    # I keep checking the shared memory until something new has
    # been written.
    while s == what_i_wrote:
        # Nothing new; give Mrs. Conclusion another chance to respond.
        if not params["LIVE_DANGEROUSLY"]:
            utils.say("Releasing the semaphore")
            semaphore.release()
            utils.say("Waiting to acquire the semaphore")
            semaphore.acquire()

        s = utils.read_from_memory(mapfile)

    # What I read must be the md5 of what I wrote or something's
    # gone wrong.
    if PY_MAJOR_VERSION > 2:
        what_i_wrote = what_i_wrote.encode()

    try:
        assert(s == hashlib.md5(what_i_wrote).hexdigest())
    except AssertionError:
        utils.raise_error(AssertionError,
                          "Shared memory corruption after %d iterations." % i)

    # MD5 the reply and write back to Mrs. Conclusion.
    if PY_MAJOR_VERSION > 2:
        s = s.encode()
    what_i_wrote = hashlib.md5(s).hexdigest()
    utils.write_to_memory(mapfile, what_i_wrote)

utils.say("")
utils.say("%d iterations complete" % (i + 1))

# Announce for one last time that the semaphore is free again so that
# Mrs. Conclusion can exit.
if not params["LIVE_DANGEROUSLY"]:
    utils.say("")
    utils.say("Final release of the semaphore followed by a 5 second pause")
    semaphore.release()
    time.sleep(5)
    # ...before beginning to wait until it is free again.
    # Technically, this is bad practice. It's possible that on a
    # heavily loaded machine, Mrs. Conclusion wouldn't get a chance
    # to acquire the semaphore. There really ought to be a loop here
    # that waits for some sort of goodbye message but for purposes of
    # simplicity I'm skipping that.
    utils.say("Final wait to acquire the semaphore")
    semaphore.acquire()

utils.say("Destroying semaphore and shared memory.")
mapfile.close()
# I could call memory.unlink() here but in order to demonstrate
# unlinking at the module level I'll do it that way.
posix_ipc.unlink_shared_memory(params["SHARED_MEMORY_NAME"])

semaphore.release()

# I could also unlink the semaphore by calling
# posix_ipc.unlink_semaphore() but I'll do it this way instead.
semaphore.unlink()
