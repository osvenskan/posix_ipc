# POSIX IPC

`posix_ipc` is a Python module (written in C) that permits creation and manipulation of POSIX inter-process semaphores, shared memory and message queues on platforms supporting the POSIX Realtime Extensions a.k.a. POSIX 1003.1b-1993. This includes nearly all Unices and Windows + Cygwin ≥ 1.7.

`posix_ipc` is compatible with all supported versions of Python 3.

**For complete documentation, see [the usage notes](USAGE.md).**

## Python 2.7 Support

Version 1.0.5 was the last version of `posix_ipc` to support both Python 2.7 and Python 3.x. Starting with version 1.1.0, only Python ≥ 3.6 is supported. No changes (neither fixes nor features) will be backported to 1.0.5.

## Installation

`posix_ipc` is available on PyPI:

`pip install posix-ipc`

Or you can clone the project and install it using `setup.py`:

`python setup.py install`

## License

`posix_ipc` is free software (free as in speech and free as in beer) released under a 3-clause BSD license. Complete licensing information is available in [the LICENSE file](LICENSE).

## Related

You might also be interested in the similar System V IPC module: https://github.com/osvenskan/sysv_ipc
