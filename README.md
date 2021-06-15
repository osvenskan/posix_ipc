# POSIX IPC

`posix_ipc` is a Python module (written in C) that permits creation and manipulation of POSIX inter-process semaphores, shared memory and message 
queues on platforms supporting the POSIX Realtime Extensions a.k.a. POSIX 1003.1b-1993. This includes nearly all Unices and Windows + Cygwin 1.7.

`posix_ipc` is compatible with both Python 2 and 3.

## Installation

`posix_ipc` is available on PyPI:

`$ pip install posix-ipc`

Or you can clone the project and install it using `pip`:

`pip setup.py install`

## Supported Features

* POSIX Semaphores
* POSIX Shared Memory
* POSIX Message Queue

## License

`posix_ipc` is free software (free as in speech and free as in beer) released under a 3-clause BSD license. Complete licensing information is available in the LICENSE file.

## Related

You might also be interested in the similar System V IPC module at:
http://semanchuk.com/philip/sysv_ipc/
