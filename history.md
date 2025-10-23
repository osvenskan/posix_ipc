# The posix_ipc Module for POSIX IPC Under Python — Version History

This is the version history for the [posix_ipc module](https://github.com/osvenskan/posix_ipc).

I consider this module complete. I will continue to support it, and I'm open to adding useful features, but right now I don't see any.

# Current/Latest – 1.3.2 (22 Oct 2025)

This release fixes a buglet introduced yesterday in 1.3.1 in `MessageQueue.receive()`. Cleanup of the message and priority was not handled correctly under some conditions. Dziękuję to [Szymon Janora](https://github.com/szymon-janora) for the PR (https://github.com/osvenskan/posix_ipc/pull/95).

Please keep in mind that the module constants `PAGE_SIZE` and `SEMAPHORE_VALUE_MAX` have been deprecated as of version 1.3.0 (see below). They will be removed in a future version.

# Older Versions

## 1.3.1 (21 Oct 2025)

This release features two small changes --

 - Fixed a bug (introduced in 1.3.0) where system discovery failed if the `CC` environment variable contained flags. Thanks to [HaixiaoYanWind](https://github.com/HaixiaoYanWind) for the bug report and PR (https://github.com/osvenskan/posix_ipc/pull/92).
 - Improved the performance of the `MessageQueue.receive()` method by eliminating one copy operation. If you receive a lot of long messages, you might notice a 5-10% improvement in the performance of `receive()`. Dziękuję to [Szymon Janora](https://github.com/szymon-janora) for the PR (https://github.com/osvenskan/posix_ipc/pull/75).

Please keep in mind that the module constants `PAGE_SIZE` and `SEMAPHORE_VALUE_MAX` have been deprecated as of version 1.3.0 (see below). They will be removed in a future version.

## 1.3.0 (29 July 2025)

The goal of this release is to make the build process more robust and flexible. This should make life easier for those who are cross compiling `posix_ipc`.

*There are no changes to the core code in this release. There are, however, two deprecated constants, and many changes to how the module's build system collects information from the host system.* This is the first significant update to this code in 17 years. I hope I didn't introduce too many new bugs. 😬

### Deprecations

> [!IMPORTANT]
> The module constants `PAGE_SIZE` and `SEMAPHORE_VALUE_MAX` are deprecated as of this version. They will be removed in a future version. See https://github.com/osvenskan/posix_ipc/issues/81 for background.

### Changes to System Discovery

 - `discover_system_info.py` now raises `DiscoveryError` if it encounters a situation it can't handle.
 - `discover_system_info.py` now emits `POSIXNonComplianceWarning` if it detects that the host (build) system is not POSIX compliant.
 - Prioritized `os.sysconf()` as a source of system information where possible, especially over compilation.
 - Improved `does_build_succeed()` and `compile_and_run()`, including some ideas suggested by [Martin Jansa](https://github.com/shr-project) in https://github.com/osvenskan/posix_ipc/pull/77.
 - Added and expanded docstrings.
 - Removed some platform-specific comments that were mostly speculative and out of date.
 - Changed to always write `SEM_VALUE_MAX` to `system_info.h`, and surround it with `#ifndef/#endif`.

### Other Changes

- Fixed a bug (https://github.com/osvenskan/posix_ipc/issues/82) introduced in 1.2.0 where a custom `system_info.h` was ignored.
- Added a sample file (`system_info.sample.h`) that can be used as a template for writing your own.
- Updated `USAGE.md` with more details about module constants.
- Added macOS 15 wheels.
- Reformatted this file.
- Added `CONTRIBUTORS.txt` and updated copyright notices to address https://github.com/osvenskan/posix_ipc/issues/76.
- Added a GitHub issue template to make people more aware of the mailing list https://groups.io/g/python-posix-ipc/topics.

## 1.2.0 (16 April 2025)

This release modernizes the file layout, building, and packaging of `posix_ipc`. There are no changes to the core code.

 - Thanks to [Matiiss](https://github.com/Matiiss), this version integrates with `cibuildwheel` to automate testing and create wheels for many platforms.
 - The `discover_system_info.py` script (formerly `prober.py`) now respects the `CC` environment variable instead of using a hardcoded `cc` to launch the compiler. Thanks to [György Sárvári](https://github.com/OldManYellsAtCloud) for the patch.
 - Added `building.md` to begin documenting `discover_system_info.py` and the header file it creates.
 - Modernized the project to use `pyproject.toml` and modern build practices (e.g. `python -m build`). I reorganized the project's files to make it easier to use `pyproject.toml`.

## 1.1.1 (31 December 2022)

 - Fixed a bug introduced in 1.1.0 where setup would fail on systems where [the default file system encoding is not UTF-8](https://github.com/osvenskan/posix_ipc/issues/40).
 - Made message queue tests more conservative to avoid resource exhaustion that [could occur on a system with an atypical configuration](https://github.com/osvenskan/posix_ipc/issues/42).
 - Fixed (again) [a test bug related to shared memory size](https://github.com/osvenskan/posix_ipc/issues/35), this time for real! Thanks to [Rudolf Hornig](https://github.com/rhornig) for the fix.

## 1.1.0 (25 November 2022)

 - Drop support for Python 2.7 and ≤ 3.6.
 - Converted doc to Markdown. Thanks to [Bahram Aghaei](https://github.com/GreatBahram) and [Chris Kitras](https://github.com/christopolise).
 - On macOS, relax a test related to shared memory size (https://github.com/osvenskan/posix_ipc/issues/35).

## 1.0.5 (10 October 2020)

This is the last version to support Python 2.7.

 - Added a `fileno` method to `SharedMemory` and `MessageQueue` objects to support Python's `selectors` standard library module.
 - Added a demo (in the demo5 directory) demonstrating use of `selectors`. *Mange tak* to [Henrik Enggaard](https://github.com/henrikh) for the `fileno()` suggestion and for contributing the demo.
 - Added automatic Travis testing on GitHub for Python 3.7 thanks to Ben Harper, and for Python 2.7 under macOS.
 - Fixed a [deprecation warning under Python 3.9](https://github.com/osvenskan/posix_ipc/issues/22). *Merci* to sbraz for the bug report.
 - Updated HTML documentation (including this file) to HTML 5.

## 1.0.4 (13 Feb 2018)

 - Fixed bug where the `SharedMemory` and `Semaphore` classes [didn't behave correctly](https://github.com/osvenskan/posix_ipc/issues/2) when assigned a file descriptor of 0. Thanks to Thomas Troeger for the bug report.
 - Fixed a small but [significant documentation bug](https://github.com/osvenskan/posix_ipc/issues/3) which stated that the `size` param was ignored when opening an existing `SharedMemory` segment. Thanks to Thomas Troeger, again.
 - Fixed a compilation failure under Python 3 when the internal use `POSIX_IPC_DEBUG` flag was on. Děkuji to Tomáš Zahradnický for the bug report.

## 1.0.3 (10 Jan 2018)
    
A *mea culpa* release to clean up some accumulated technical debt.

 - Moved repository to git and GitHub.
 - Changed link options in the build script for the first demo that caused a build fail on some (all?) Linuxes.
 - Fix a few bugs where functions that were documented to accept keyword arguments only accepted them as positional arguments; added tests to exercise keyword arguments.
 - Removed dependency on `setuptools` from `setup.py`.
 - Added code to semaphore tests to avoid triggering a bug on older FreeBSDs (and perhaps other BSDs).
 - PEP8 improvements.

## 1.0.2 (10 Jan 2018)
    
This version was also skipped due to a release error. Those responsible for sacking the people who have just been sacked, have been sacked.

## 1.0.1 (10 Jan 2018)
    
This version was skipped due to a release error. Those responsible have been sacked.

## 1.0.0 (11 Mar 2015)

 - Added ability to pass names as unicode in Python 2.
 - Added ability to pass names as bytes in Python 3.
 - Dropped support for Python < 2.7.
 - Made unit tests nicer by taking advantage of Python 2.7+ certainty and removed some code that only supported Python 2.6.

## 0.9.9 (14 Nov 2014)

 - Added the ability to build on platforms that don't support the POSIX Realtime Signals Extension. ありがとう to Takashi Yamamoto for the patch.
 - Added extensive unit tests.
 - Minor documentation updates.

## 0.9.8 (20 Feb 2014)
    
As with 0.9.7, there are no code or feature changes in this version. This version merely corrects a documentation error.

This version comes with a big wish for peace in Ukraine. Мир!
    
## 0.9.7 (20 Feb 2014)
    
There are no code or feature changes in this version. The bump in version number reflects that this is the first version also available on PyPI.

This version comes with a big wish for peace in Ukraine. Мир!
    
## 0.9.6 (23 Oct 2013)
    
Fixed two BSD-specific bugs introduced in version 0.9.5 that occurred if the kernel module `mqueuefs` wasn't loaded at install time. Specifically --

 - The installer would print a harmless but distracting error message from sysctl. (This also affected OS X which is FreeBSD-ish.)
 - `posix_ipc` would build with an inappropriate value for `QUEUE_MESSAGES_MAX_DEFAULT`. Subsequent attempts to create a message queue would fail unless the caller set the `max_messages` param to an appropriate value. (This didn't affect OS X since OS X doesn't support message queues at all.)

Also, rewrote the message queue thread notification code to address the old bug (`Fatal Python error: PyEval_AcquireLock: current thread state is NULL`) that appeared during release testing for 0.9.5 and which has plagued me on and off since I wrote this code. The new code uses [the algorithm recommended in the Python documentation](http://docs.python.org/2/c-api/init.html#non-python-created-threads) which may have been flaky when I started using it in Python 2.4. It seems stable now under Python 2.6+/3.
    
## 0.9.5 (14 Oct 2013)

 - Added the ability to use Semaphores in context managers. Thanks to Matt Ruffalo for the suggestion and patch.
 - Fixed a big under FreeBSD 9.x where I used overly ambitious values for some message queue constants at build time. Now, `posix_ipc` asks `sysctl` for the correct values. *Köszönöm* to Attila Nagy for the bug report.

## 0.9.4 (2 Sept 2012)
    
Fixed a buglet. When creating shared memory under Linux and specifying both a size and the read-only flag, creating the memory would succeed but calling `ftruncate()` would fail. The failure to change the size was correctly reported but `posix_ipc` failed to clean up the shared memory segment it had created. That's now fixed. Thanks to Kevin Miles for the bug report.

## 0.9.3 (2 Jan 2012)
    
Added a bugfix/feature to raise an error (rather than segault) when trying to use a closed semaphore. Thanks to Russel for the suggestion and patch.
    
## 0.9.2 (6 Nov 2011)

 - Fixed a bug where timeouts in `Semaphore.acquire()`, `MessageQueue.send()` and `MessageQueue.receive()` were only accurate to about one second due to use of the C call `time()`. Switching to `gettimeofday()` fixes the problem. Thanks to Douglas Young for the bug report and patch.
 - Fixed a bug in `prober.py` that caused install to fail under Ubuntu 11.10. `prober.py` specified link options in the wrong order, and so linking one of the test applications that's built during setup was failing. Thanks to Kevin Miles for the bug report.
 - Added a check in `prober.py` to see if `sysconf_names` exists in the `os` module. It doesn't exist under Cygwin, and this code caused an error on that platform. Thanks to Rizwan Raza for the bug report.

## 0.9.1 (7 Apr 2011)

 - Fixed (?) a bug in message queue thread notification that caused `ceval: tstate mix-up` and other fun messages. Thanks to Lev Maximov for the bug report.
 - Added the `demo3` directory with demos of message queue. This was supposed be included in version 0.9.0 but I accidentally left it out. (Also reported by Lev.)

## 0.9.0 (31 Dec 2010)
    
Added the `demo3` directory with demos of message queue notification techniques. Also, fixed two bugs related to message queue notification. Big thanks to Philip D. Bober for debugging and providing a patch to the most difficult part of the code. The bugs were –

 - First, the series of calls to set up the Python thread in `process_notification()` were simply wrong. They worked some (most?) of the time but would segfault eventually because I was creating a Python thread state when I should not have.
 - Second, the code in `process_notification()` failed to consider that the user's callback might re-request notification, thus overwriting pointers that I would later decref. `process_notification()` is now thread-safe.

## 0.8.1 (15 Mar 2010)
    
Fixed a sloppy declaration that caused a compile error under Cygwin 1.7.1. Thanks to Jill McCutcheon for the bug report.

## 0.8.0 (2 Mar 2010)

 - Fixed message queue support detection in FreeBSD and the platform-specific documentation about FreeBSD.
 - Rearranged the documentation and split the history (which you're reading now) into a separate file.
 - I fixed two small bugs related to the confusing message queue constants. The bugs and associated changes are explained below. The explanation is really long not because the changes were big (they weren't), but because they and rationale behind them are subtle.

    Fixing these bugs was made easier by this realization: on all of the systems to which I have access that implement message queues (FreeBSD, OpenSolaris, Linux, and Windows + Cygwin), all except Linux implement them as memory-mapped files or something similar. On these non-Linux systems, the maximum queue message count and size are pretty darn big (`LONG_MAX`). Therefore, only on Linux is anyone likely to encounter limits to message queue size and content.

    The first bug I fixed was related to four message queue constants mentioned in `posix_ipc` documentation: `QUEUE_MESSAGES_MAX`, `QUEUE_MESSAGES_MAX_DEFAULT`, `QUEUE_MESSAGE_SIZE_MAX` and `QUEUE_MESSAGE_SIZE_MAX_DEFAULT`. All four were defined in the `C` code, but the two `XXX_DEFAULT` constants weren't exposed on the Python side.

    The second bug was that under Linux, `QUEUE_MESSAGES_MAX` and `QUEUE_MESSAGE_SIZE_MAX` were permanently fixed to their values at `posix_ipc`'s compile/install time even if the relevant system values changed later. Thanks to Kyle Tippetts for bringing this to my attention.

    `QUEUE_MESSAGES_MAX_DEFAULT` was arbitrarily limited to (at most) 1024. This wasn't a bug, just a bad choice.

    I made a few changes in order to fix these problems –

    1. The constants `QUEUE_MESSAGES_MAX` and `QUEUE_MESSAGE_SIZE_MAX` **have been deleted** since they were only sure to be accurate on systems where they were irrelevant. Furthermore, Linux (the only place where they matter) exposes these values through the file system (in `/proc/sys/fs/mqueue/msg_max` and `/proc/sys/fs/mqueue/msgsize_max` respectively) so Python apps that need them can read them without any help from `posix_ipc`.
    2. `QUEUE_MESSAGES_MAX_DEFAULT` and `QUEUE_MESSAGE_SIZE_MAX_DEFAULT` are now exposed to Python as they should have been all along. `QUEUE_MESSAGES_MAX_DEFAULT` is now set to `LONG_MAX` on all platforms except Linux, where it's set at compile time from `/proc/sys/fs/mqueue/msg_max`.
    3. `QUEUE_MESSAGE_SIZE_MAX_DEFAULT` remains at the fairly arbitrary value of 8k. It's not a good idea to make it too big since a buffer of this size is allocated every time `MessageQueue.receive()` is called. Under Linux, I check the contents of `/proc/sys/fs/mqueue/msgsize_max` and make `QUEUE_MESSAGE_SIZE_MAX_DEFAULT` smaller if necessary.

## 0.7.0 (21 Feb 2010)
    
Added Python 3.1 support.
    
## 0.6.3 (15 Feb 2009)

 - Fixed a bug where creating an IPC object with invalid parameters would correctly raise a `ValueError`, but with a message that may or may not have correctly identified the cause. (My code was making an educated guess that was sometimes wrong.)

 As of this version, if initialization of an IPC object fails with the error code `EINVAL`, `posix_ipc` raises a `ValueError` with the vague-but-correct message "Invalid parameter(s)".

 - Cleaned up the code a little internally.

## 0.6.2 (30 Dec 2009)
    
Fixed a bug where a `MessageQueue`'s `mode` attribute returned garbage. *Grazie* to Stefano Debenedetti for the bug report.
    
## 0.6.1 (29 Nov 2009)
    
There were no functional changes to the module in this version, but I added the convenience function `close_fd()` and fixed some docmentation and demo bugs/sloppiness.

 - Added the convenience function `SharedMemory.close_fd()`. Thanks to Kyle Tippetts for pointing out the usefulness of this.
 - Added the module attributes `__version__`, `__copyright__`, `__author__` and `__license__`.
 - Fixed the license info embedded in `posix_ipc_module.c` which was still referring to GPL.
 - Replaced `file()` in `setup.py` with `open()`/`close()`.
 - Demo changes –
    - Made the demo a bit faster, especially for large shared memory chunks. Thanks to Andrew Trevorrow for the suggestion and patch.
    - Fixed a bug in premise.c; it wasn't closing the semaphore.
    - Fixed a bug in premise.py; it wasn't closing the shared memory's file descriptor.
    - Fixed bugs in conclusion.py; it wasn't closing the shared memory's file descriptor, the semaphore or the mapfile.

## 0.6 (5 Oct 2009)

 - Relicensed from the GPL to a BSD license to celebrate the one year anniversary of this module.
 - Updated Cygwin info.

## 0.5.5 (17 Sept 2009)

 - Set `MQ_MAX_MESSAGES` and `MQ_MAX_MESSAGE_SIZE` to `LONG_MAX` under cygwin. (*Danke* to René Liebscher.)
 - Surrounded the `#define PAGE_SIZE` in probe_results.h with `#ifndef/#endif` because it is already defined on some systems. (*Danke* to René Liebscher, again.)
 - Minor documentation changes.

## 0.5.4 (21 Jun 2009)

 - Added SignalError.
 - Fixed a bug where [Python would generate an uncatchable KeyboardInterrupt when Ctrl-C was hit during a wait](http://groups.google.com/group/comp.lang.python/browse_thread/thread/ada39e984dfc3da6/fd6becbdce91a6be?#fd6becbdce91a6be) (e.g. `sem.acquire()`).

  Thanks to Maciek W. for reporting the problem and to Piet van Oostrum and Greg for help with a solution.

 - Minor documentation changes.

## 0.5.3 (8 Mar 2009)

 - Added automatic generation of names.
 - Changed status to beta.

## 0.5.2 (12 Feb 2009)

 - Fixed a memory leak in `MessageQueue.receive()`.
 - Fixed a bug where the name of the `MessageQueue` `current_messages` attribute didn't match the name given in the documentation.
 - Added the `VERSION` attribute to the module.
 - Fixed a documentation bug that said message queue notifications were not yet supported.

## 0.5.1 (8 Feb 2009)

Fixed outdated info in `setup.py` that was showing up in the Python package index. Updated `README` while I was at it.

## 0.5 (8 Feb 2009)

 - Added the message queue notification feature.
 - Added a `mode` attribute to each type.
 - Added `str()` and `repr()` support to each object.
 - Added a demo for message queues.
 - Fixed some minor documentation problems and added some information (esp. about Windows + Cygwin).

## 0.4 (9 Jan 2009) –

 - Added message queue support.
 - Fixed the poor choices I'd made for names for classes and errors by removing the leading "Posix" and "PosixIpc".
 - Simplified the prober and expanded it (for message queue support).
 - Cleaned up this documentation.

## 0.3.2 (4 Jan 2009)

 - Fixed an uninitialized value passed to PyMem_Free() when invalid params were passed to either constructor.

## 0.3.1 (1 Jan 2009)

 - Fixed a big bug where the custom exceptions defined by this module weren't visible.
 - Fixed a compile complaint about the redefinition of `SEM_VALUE_MAX` on Linux (Ubuntu) that I introduced in the previous version.
 - Fixed a bug in the demo program premise.c where I wasn't closing the file descriptor associated with the shared memory.
 - Added the `PAGE_SIZE` attribute. This was already available in the mmap module that you need to use shared memory anyway, but adding it makes the interface more consistent with the `sysv_ipc` module.

## 0.3 (19 Dec 2008)

 - Added informative custom errors instead of raising OSError when something goes wrong.
 - Made the code friendly to multi-threaded applications.
 - Added the constants `O_CREX` and `SEMAPHORE_VALUE_MAX`.
 - Added code to prohibit negative timeout values.

## 0.2 (4 Dec 2008)

 - Removed the un-Pythonic `try_acquire()` method. The same functionality is now available by passing a timeout of `0` to the `.acquire()` method.
 - Renamed the module constant `ACQUIRE_TIMEOUT_SUPPORTED` to `SEMAPHORE_TIMEOUT_SUPPORTED`.
 - Moved the demo code into its own directory and added C versions of the Python scripts. The parameters are now in a text file shared by the Python and C program, so you can run the C version of Mrs. Premise and have it communicate with the Python version of Mrs. Conclusion and vice versa.

## 0.1 (9 Oct 2008)

Original (alpha) version.
