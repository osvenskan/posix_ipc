# Building/Compiling POSIX IPC

You can build `posix_ipc` with a normal build command like `python -m build`. This document describes an unusual step that happen at build time.

## System Information Discovery

`posix_ipc` needs to know various IPC-related facts about its host system. For instance, some operating systems don't offer a timed wait function for semaphores. This module wants to make that functionality available when it's present, and also needs to know when it's not present and therefore can't be called.

This kind of information needs to be known before `posix_ipc` is compiled. To get that information, `build_support/discover_system_info.py` runs when `setup.py` is invoked. Here's some information about that script.

## The Script

The best documentation for the script is currently the script itself. I hope to provide more formal documentation in a future release. Please don't laugh at the code too much. It's been adjusted over the years, but the core of it was written in 2008 when both Python and I had different standards. In releases prior to 1.2, this script was called `prober.py`.

The script typically writes a C header file which is described below.

## The Header File

The goal of `discover_system_info.py` is to write `src/system_info.h`. (In releases prior to 1.2, this file was called `probe_results.h`.) This header file isn't part of the source distribution, nor should it be. It contains values that are specific to the system on which `posix_ipc` is built.

If the file exists when `discover_system_info.py` runs, it will not be overwritten. This allows developers to create their own `system_info.h` (to enable debugging messages from `posix_ipc`, for instance.)

It's critical to understand that the values in the header file _describe_ your system to `posix_ipc`. They don't change the behavior of your operating system. For instance, if you decide to change `SEM_VALUE_MAX` to a larger number, that won't actually increase the maximum valid value for a semaphore on your system. It will only misinform `posix_ipc` about what your system accepts, and a misinformed `posix_ipc` will probably behave badly.

### Header File Values

These are the `#define` values that can appear in the header file. The format of this file might change in a future release; see https://github.com/osvenskan/posix_ipc/issues/62

 - `POSIX_IPC_VERSION` - A string, e.g. "1.1.1"

 - `POSIX_IPC_DEBUG` - A boolean. If present, `posix_ipc` will print messages to `stderr` as it runs. (Use this with care; it's a developer-only feature and the implementation isn't very robust.)

 - `REALTIME_LIB_IS_NEEDED` - A boolean. If present, then the setup procedure will link to `librt` at build time. If absent, the setup procedure will not link to `librt`.

 - `PAGE_SIZE` - An integer, e.g. 8192

 - `SEM_GETVALUE_EXISTS` - A boolean. If present, then the OS supports `sem_getvalue()`, so `posix_ipc` can implement `Semaphore.value`. If not present, `sem_getvalue()` isn't supported, so `Semaphore.value` will raise an `AttributeError`.

 - `SEM_TIMEDWAIT_EXISTS` - A boolean. If present, then the OS supports `sem_timedwait()`, so `posix_ipc` can enable `Semaphore.acquire()` with timeouts other than 0 and infinite. If not present, `sem_timedwait()` isn't supported. (See [the documentation for `Semaphore.acquire()`](usage.md#semaphore-acquire-method.)

 - `SEM_VALUE_MAX` - An integer that describes the maximum value of a semaphore, e.g. 32767

 - `MESSAGE_QUEUE_SUPPORT_EXISTS` - A boolean. If present, then the host system implements POSIX message queues. If not present, `posix_ipc` can't offer any `MessageQueue` features. (Mac OS is an example of a platform that doesn't implement POSIX message queues.)

 - `QUEUE_MESSAGES_MAX_DEFAULT` - A integer, e.g. 10. When creating a message queue, this value is supplied for the queue's `max_messages` parameter if one isn't specified by the caller.

 - `QUEUE_MESSAGE_SIZE_MAX_DEFAULT` - A integer, e.g. 8192. When creating a message queue, this value is supplied for the queue's `max_message_size` parameter if one isn't specified by the caller.

 - `QUEUE_PRIORITY_MAX` - A integer, e.g. 32, that describes the largest priority value that a message can have.
