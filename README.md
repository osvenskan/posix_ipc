# POSIX IPC

`posix_ipc` is a Python module (written in C) that permits creation and manipulation of POSIX inter-process semaphores, shared memory and message queues on platforms supporting the POSIX Realtime Extensions a.k.a. POSIX 1003.1b-1993. This includes nearly all Unices, and Windows + Cygwin ≥ 1.7.

**For complete documentation, see [the usage notes](USAGE.md).**

`posix_ipc` is compatible with all supported versions of Python 3. Older versions of `posix_ipc` may [still work under Python 2.x](USAGE.md#support-for-older-pythons).

If you want to build your own copy of `posix_ipc`, see [the build notes](building.md).

## Installation

`posix_ipc` is available from PyPI:

	pip install posix-ipc

If you have the source code, you can install `posix_ipc` with this command:

	python -m pip install .

## Tests

`posix_ipc` has a robust test suite. To run tests --

	python -m unittest discover --verbose

## License

`posix_ipc` is free software (free as in speech and free as in beer) released under a 3-clause BSD license. Complete licensing information is available in [the LICENSE file](LICENSE).

## Support

If you have comments, questions, or ideas to share, please use the mailing list:
https://groups.io/g/python-posix-ipc/

If you think you've found a bug, you can file an issue on GitHub:
https://github.com/osvenskan/posix_ipc/issues

Please note that as of this writing (2025), it's been seven years since anyone found a bug in the core code, so maybe ask on the mailing list first. 🙂

## Related

You might also be interested in the similar System V IPC module: https://github.com/osvenskan/sysv_ipc
