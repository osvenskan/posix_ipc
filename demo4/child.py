import posix_ipc
import time
import sys
import random

# The parent passes the semaphore's name to me.
name = sys.argv[1]

print('Child: waiting to aquire semaphore ' + name)

with posix_ipc.Semaphore(name) as sem:
    print('Child: semaphore ' + sem.name + ' aquired; holding for 3 seconds.')

    # Flip a coin to determine whether or not to bail out of the context.
    if random.randint(0, 1):
        print("Child: raising ValueError to demonstrate unplanned context exit")
        raise ValueError

    time.sleep(3)

    print('Child: gracefully exiting context (releasing the semaphore).')
