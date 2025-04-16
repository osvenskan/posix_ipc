import subprocess
import posix_ipc
import time
import os

sem = posix_ipc.Semaphore(None, posix_ipc.O_CREX, initial_value=1)
print("Parent: created semaphore {}.".format(sem.name))

sem.acquire()

# Spawn a child that will wait on this semaphore.
path, _ = os.path.split(__file__)
print("Parent: spawning child process...")
subprocess.Popen(["python", os.path.join(path, 'child.py'), sem.name])

for i in range(3, 0, -1):
    print("Parent: child process will acquire the semaphore in {} seconds...".format(i))
    time.sleep(1)

sem.release()

# Sleep for a second to give the child a chance to acquire the semaphore.
# This technique is a little sloppy because technically the child could still
# starve, but it's certainly sufficient for this demo.
time.sleep(1)

# Wait for the child to release the semaphore.
print("Parent: waiting for the child to release the semaphore.")
sem.acquire()

# Clean up.
print("Parent: destroying the semaphore.")
sem.release()
sem.unlink()

msg = """
By the time you're done reading this, the parent will have exited and so the
operating system will have destroyed the semaphore. You can prove that  the
semaphore is gone by running this command and observing that it raises
posix_ipc.ExistentialError --

   python -c "import posix_ipc; posix_ipc.Semaphore('{}')"

""".format(sem.name)

print(msg)
