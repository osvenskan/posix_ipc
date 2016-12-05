# Python modules
import gc
import os
import subprocess
import random
import re
import sys

# My module
import posix_ipc

# TEST_COUNT = 10
TEST_COUNT = 1024 * 102

SKIP_SEMAPHORE_TESTS = False
SKIP_SHARED_MEMORY_TESTS = False
SKIP_MESSAGE_QUEUE_TESTS = False

if not posix_ipc.MESSAGE_QUEUES_SUPPORTED:
    SKIP_MESSAGE_QUEUE_TESTS = False

# ps output looks like this:
#   RSZ      VSZ
#   944    75964
ps_output_regex = re.compile("""
    ^
    \s*   # whitespace before first heading
    \S*   # first heading (e.g. RSZ)
    \s+   # whitespace between headings
    \S*   # second heading (e.g VSZ)
    \s+   # newline and whitespace before first numeric value
    (\d+) # first value
    \s+   # whitespace between values
    (\d+) # second value
    \s*   # trailing whitespace if any
    $
""", re.MULTILINE | re.VERBOSE)

# On OS X, Ubuntu and OpenSolaris, both create/destroy tests show some growth
# is rsz and vsz. (e.g. 3248 versus 3240 -- I guess these are measured
# in kilobytes?) When I increased the number of iterations by a factor of 10,
# the delta didn't change which makes me think it isn't an actual leak
# but just some memory consumed under normal circumstances.

# When I created an intentional leak by commenting out the call to
# PyMem_Free(self->name);  in Semaphore_dealloc(), here's what
# happened to the memory usage:
#    Memory usage before, RSS = 3264, VSZ = 84116
#    Python's GC reports no leftover garbage
#    Memory usage after, RSS = 19912, VSZ = 100500


NAME_CHARACTERS = "abcdefghijklmnopqrstuvwxyz"
NAME_LENGTH = 10


PY_MAJOR_VERSION = sys.version_info[0]


def say(s):
    """A wrapper for print() that's compatible with Python 2 & 3"""
    print(s)


def random_string(length):
    return ''.join(random.sample("abcdefghijklmnopqrstuvwxyz", length))


def print_mem_before():
    say("Memory usage before, RSS = %d, VSZ = %d" % get_memory_usage())


def print_mem_after():
    gc.collect()

    if gc.garbage:
        say("Leftover garbage:" + str(gc.garbage))
    else:
        say("Python's GC reports no leftover garbage")

    say("Memory usage after, RSS = %d, VSZ = %d" % get_memory_usage())


def get_memory_usage():
    # `ps` has lots of format options that vary from OS to OS, and some of
    # those options have aliases (e.g. vsz, vsize). The ones I use below
    # appear to be the most portable.
    s = subprocess.Popen(["ps", "-p", str(os.getpid()), "-o", "rss,vsz"],
                         stdout=subprocess.PIPE).communicate()[0]

    # Output looks like this:
    #   RSZ      VSZ
    #   944    75964

    if PY_MAJOR_VERSION > 2:
        s = s.decode(sys.getfilesystemencoding())

    m = ps_output_regex.match(s)

    rsz = int(m.groups()[0])
    vsz = int(m.groups()[1])

    return rsz, vsz

    # chunks = [ item for item in s.split(' ') if item.strip() ]
    #
    # rss = chunks[0]
    # vsize = chunks[1]
    #
    # rss = int(rss.strip())
    # vsize = int(vsize.strip())
    #
    # return rss, vsize


# Assert manual control over the garbage collector
gc.disable()

the_range = range(TEST_COUNT)

if SKIP_SEMAPHORE_TESTS:
    say("Skipping semaphore tests")
else:
    say("Running semaphore create/destroy test...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        sem = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
        sem.close()
        sem.unlink()

    print_mem_after()

    say("Running semaphore create/destroy test 2...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        sem = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
        sem.close()
        posix_ipc.unlink_semaphore(name)

    print_mem_after()

    say("Running semaphore create/destroy test 3...")
    print_mem_before()

    for i in the_range:
        sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX)
        sem.close()
        sem.unlink()

    print_mem_after()

    say("Running semaphore create/destroy test 4...")
    print_mem_before()

    name = "/abcdefghijklm"
    sem = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
    for i in the_range:
        try:
            foo = posix_ipc.Semaphore(name, posix_ipc.O_CREX)
        except posix_ipc.ExistentialError:
            pass

    sem.close()
    posix_ipc.unlink_semaphore(name)

    print_mem_after()

    say("Running semaphore acquire/release test...")
    print_mem_before()

    sem = posix_ipc.Semaphore("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        sem.release()
        sem.acquire()

    sem.close()
    sem.unlink()

    print_mem_after()

    if posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED:
        say("Running semaphore acquire timeout test...")
        print_mem_before()

        sem = posix_ipc.Semaphore("/p_ipc_test", posix_ipc.O_CREX)

        for i in the_range:
            try:
                sem.acquire(.001)
            except posix_ipc.BusyError:
                pass

        sem.close()
        sem.unlink()

        print_mem_after()
    else:
        say("Skipping semaphore acquire timeout test (not supported on this platform)")

    say("Running semaphore name read test...")
    print_mem_before()

    sem = posix_ipc.Semaphore("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = sem.name

    sem.close()
    sem.unlink()

    print_mem_after()

    if posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
        say("Running semaphore value read test...")
        print_mem_before()

        sem = posix_ipc.Semaphore("/p_ipc_test", posix_ipc.O_CREX)

        for i in the_range:
            foo = sem.value

        sem.close()
        sem.unlink()

        print_mem_after()
    else:
        say("Skipping semaphore value read test (not supported on this platform)")


# ============== Memory tests ==============

if SKIP_SHARED_MEMORY_TESTS:
    say("Skipping shared memory tests")
else:
    say("Running memory create/destroy test...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        mem = posix_ipc.SharedMemory(name, posix_ipc.O_CREX, size=4096)

        os.close(mem.fd)

        mem.unlink()

    print_mem_after()

    say("Running memory create/destroy test 2...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        mem = posix_ipc.SharedMemory(name, posix_ipc.O_CREX, size=4096)

        os.close(mem.fd)

        posix_ipc.unlink_shared_memory(name)

    print_mem_after()

    say("Running memory create/destroy test 3...")
    print_mem_before()

    for i in the_range:
        mem = posix_ipc.SharedMemory(None, posix_ipc.O_CREX, size=4096)

        os.close(mem.fd)

        mem.unlink()

    print_mem_after()

    say("Running memory name read test...")
    print_mem_before()

    mem = posix_ipc.SharedMemory("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mem.name

    mem.unlink()

    print_mem_after()

    say("Running memory fd read test...")
    print_mem_before()

    mem = posix_ipc.SharedMemory("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mem.fd

    mem.unlink()

    print_mem_after()

    say("Running memory size read test...")
    print_mem_before()

    mem = posix_ipc.SharedMemory("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mem.size

    mem.unlink()

    print_mem_after()

    say("Running memory size read test 2...")
    print_mem_before()

    mem = posix_ipc.SharedMemory("/p_ipc_test", posix_ipc.O_CREX, size=4096)

    for i in the_range:
        foo = mem.size

    mem.unlink()

    print_mem_after()

# ============== Message queue tests ==============

if SKIP_MESSAGE_QUEUE_TESTS:
    say("Skipping message queue tests")
else:
    say("Running message queue create/destroy test...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)

        mq.close()
        mq.unlink()

    print_mem_after()

    say("Running message queue create/destroy test 2...")
    print_mem_before()

    for i in the_range:
        name = "/" + ''.join(random.sample(NAME_CHARACTERS, NAME_LENGTH))
        mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)

        mq.close()
        posix_ipc.unlink_message_queue(name)

    print_mem_after()

    say("Running message queue create/destroy test 3...")
    print_mem_before()

    for i in the_range:
        mq = posix_ipc.MessageQueue(None, posix_ipc.O_CREX)
        mq.close()
        mq.unlink()

    print_mem_after()

    say("Running message queue create/destroy test 4...")
    print_mem_before()

    name = "/abcdefghijklm"
    mq = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)
    for i in the_range:
        try:
            foo = posix_ipc.MessageQueue(name, posix_ipc.O_CREX)
        except posix_ipc.ExistentialError:
            pass

    mq.close()
    posix_ipc.unlink_message_queue(name)

    print_mem_after()

    say("Running message queue send/receive() test with strings...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        mq.send(random_string(15))
        mq.receive()

    mq.close()
    mq.unlink()

    print_mem_after()

    if PY_MAJOR_VERSION > 2:
        say("Running message queue send/receive() test with bytes...")
        print_mem_before()

        mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

        for i in the_range:
            mq.send(random_string(15).encode("utf-8"))
            mq.receive()

        mq.close()
        mq.unlink()

        print_mem_after()

    say("Running lame message queue request_notification() test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        mq.request_notification(posix_ipc.USER_SIGNAL_MIN)
        mq.request_notification(None)

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue name read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.name

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue mqd read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.mqd

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue block read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.block

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue block write test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    foo = mq.block
    for i in the_range:
        mq.block = foo

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue max_messages read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.max_messages

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue max_message_size read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.max_message_size

    mq.close()
    mq.unlink()

    print_mem_after()

    say("Running  message queue current_messages read test...")
    print_mem_before()

    mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREX)

    for i in the_range:
        foo = mq.current_messages

    mq.close()
    mq.unlink()

    print_mem_after()
