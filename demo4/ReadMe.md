This demonstrates the use of a semaphore with a Python context manager (a 
'with' statement).

To run the demo, simply run `python parent.py`. It launches child.py.

The programs parent.py and child.py share a semaphore; the latter acquires the
semaphore via a context manager. The child process deliberately kills itself via
an error about half the time (randomly) in order to demonstrate that the
context manager releases the semaphore regardless of whether or not the context
block is exited gracefully.

Once the child releases the semaphore, the parent destroys it.

The whole thing happens in less than 10 seconds.

