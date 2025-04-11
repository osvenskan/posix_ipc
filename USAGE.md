# POSIX IPC for Python - Semaphores, Shared Memory and Message Queues

The Python extension module `posix_ipc` gives Python access to POSIX interprocess semaphores, shared memory and message queues on systems that support the POSIX Realtime Extensions a.k.a. POSIX 1003.1b-1993. That includes most (all?) Linuxes with kernel ≥ 2.6, FreeBSD ≥ 7.2, and OpenSolaris ≥ 2008.05. This module doesn't support unnamed (anonymous) POSIX semaphores. It is released under [a BSD license](LICENSE).

Mac and other Unix-y platforms (including Windows + [Cygwin 1.7](http://www.cygwin.com/)) provide partial (or partially broken) support. See [the platform notes below](#platform-notes) for more details.

This extension allows Python to interact with non-Python apps via IPC. If you want IPC between Python apps, you're better off using the [`multiprocessing` module](https://docs.python.org/3/library/multiprocessing.html) or the [`multiprocessing.shared_memory module`](https://docs.python.org/3/library/multiprocessing.shared_memory.html) from Python's standard library.

The [source code for `posix_ipc` is on GitHub](https://github.com/osvenskan/posix_ipc/), along with [some sample code](#sample-code).

You might want to read [all of the changes in this version](history.md) and about some [known bugs](#known-bugs).

You might be interested in the very similar module [`sysv_ipc` which provides Python access to IPC using System V semaphores, shared memory and message queues](https://github.com/osvenskan/sysv_ipc/). System V IPC has broader OS support, but many people find it less easy to use.

# Module `posix_ipc` Documentation

Jump to [semaphores](#the-semaphore-class), [shared memory](#the-sharedmemory-class), or [message queues](#the-messagequeue-class).

### Module Functions

`unlink_semaphore(name)`

`unlink_shared_memory(name)`

`unlink_message_queue(name)`

Convenience functions that unlink the IPC object described by *name*.

### Module Constants

`O_CREX, O_CREAT, O_EXCL and O_TRUNC`

These flags are used when creating IPC objects. All except `O_CREX` are bitwise unique and can be ORed together. `O_CREX` is shorthand for `O_CREAT | O_EXCL`.
`O_TRUNC` is only useful when creating SharedMemory objects.
<br><br>

`PAGE_SIZE`

The operating system's memory page size, in bytes. It's probably a good idea to make shared memory segments some multiple of this size.
<br><br>

`SEMAPHORE_TIMEOUT_SUPPORTED`

True if the underlying OS supports `sem_timedwait()`. If False, all timeouts > 0 passed to a semaphore's `acquire()` method are treated as infinity.
As far as I know, this is only False under macOS.
<br><br>

`SEMAPHORE_VALUE_SUPPORTED`

True if the underlying OS supports `sem_getvalue()`. If False, accessing the `value` attribute on a `Semaphore` instance will raise an AttributeError.
As far as I know, this is only False under macOS.
<br><br>

`SEMAPHORE_VALUE_MAX`

The maximum value that can be assigned to a semaphore.
<br><br>

`MESSAGE_QUEUES_SUPPORTED`

True if the underlying OS supports message queues, False otherwise.
<br><br>

`QUEUE_MESSAGES_MAX_DEFAULT`

The default value for a message queue's `max_messages` attribute. This can be quite small under Linux (e.g. 10) but is usually LONG_MAX everywhere else.
<br><br>

`QUEUE_MESSAGE_SIZE_MAX_DEFAULT`

The default value for a message queue's `max_message_size` attribute. This is 8k (or possibly smaller under Linux).
<br><br>

`QUEUE_PRIORITY_MAX`

The maximum message queue message priority.
<br><br>

`USER_SIGNAL_MIN, USER_SIGNAL_MAX`

The constants define a range of signal values reserved for use by user applications (like yours). They're available only on systems that support the POSIX Realtime Signals Extension. Most systems do; NetBSD versions prior to 6.0 are a notable exception.
<br><br>

`VERSION`

The module version string, e.g. `'0.9.8'`. This is also available as `__version__`.
<br><br>

### Module Errors

In addition to standard Python errors (e.g. `ValueError`), this module raises custom errors. These errors cover situations specific to IPC.

`Error`

The base error class for all the custom errors in this module.
<br><br>

`SignalError`

Raised when a waiting call (e.g. `sem.acquire()`) is interrupted by a signal other than KeyboardInterrupt.
<br><br>

`PermissionsError`

Indicates that you've attempted something that the permissions on the IPC object don't allow.
<br><br>

`ExistentialError`

Indicates an error related to the existence or non-existence of an IPC object.
<br><br>


`BusyError`

Raised when a call times out.

## The Semaphore Class

This is a handle to a semaphore.

### Constructor

`Semaphore(name, [flags = 0, [mode = 0600, [initial_value = 0]]])`

Creates a new semaphore or opens an existing one.

*name* must be `None` or a string. If it is `None`, the module chooses a random unused name. If it is a string, it should begin with a slash and be valid according to pathname rules on your system, e.g. `/wuthering_heights_by_semaphore`

The *flags* specify whether you want to create a new semaphore or open an existing one.

- With *flags* set to the default of `0`, the module attempts to open an existing semaphore and raises an error if that semaphore doesn't exist.
- With *flags* set to `O_CREAT`, the module opens the semaphore if it exists (in which case mode and initial value are ignored) or creates it if it doesn't.
- With *flags* set to `O_CREAT | O_EXCL` (or `O_CREX`), the module creates a new semaphore identified by *name*. If a semaphore with that name already exists, the call raises an `ExistentialError`.

### Instance Methods

`acquire([timeout = None])`

Waits (conditionally) until the semaphore's value is > 0 and then returns, decrementing the semaphore.

The *timeout* (which can be a float) specifies how many seconds this call should wait, if at all.

- A *timeout* of None (the default) implies no time limit. The call will not return until its wait condition is satisfied.
- When *timeout* is 0, the call immediately raises a `BusyError` if asked to wait. Since it will return immediately if not asked to wait, this can be thought of as "non-blocking" mode.
    
    This behavior is unaffected by whether or not the platform supports `sem_timedwait()` (see below).
    
- When the *timeout* is > 0, the call will wait no longer than *timeout* seconds before either returning (having acquired the semaphore) or raising a `BusyError`.
    
    On platforms that don't support the `sem_timedwait()` API, a *timeout* > 0 is treated as infinite. The call will not return until its wait condition is satisfied.
    
    Most platforms provide `sem_timedwait()`. macOS is a notable exception. The module's Boolean constant `SEMAPHORE_TIMEOUT_SUPPORTED` is True on platforms that support `sem_timedwait()`.
<br><br>

`release()`

Releases (increments) the semaphore.
<br><br>

`close()`

Closes the semaphore, indicating that the current *process* is done with the semaphore. The effect of subsequent use of the semaphore by the current process is undefined. Assuming it still exists, (see `unlink()`, below) the semaphore can be re-opened.

You must call `close()` explicitly; it is **not** called automatically when a Semaphore object is garbage collected.
<br><br>

`unlink()`

Destroys the semaphore, with a caveat. If any processes have the semaphore open when unlink is called, the call to unlink returns immediately but destruction of the semaphore is postponed until all processes have closed the semaphore.

Note, however, that once a semaphore has been unlinked, calls to `open()` with the same name should refer to a new semaphore. Sound confusing? It is, and you'd probably be wise structure your code so as to avoid this situation.
<br><br>

### Instance Attributes

`name` **(read-only)**

The name provided in the constructor.
<br><br>

`value` **(read-only)**

The integer value of the semaphore. Not available on macOS. (See [Platforms](#platform-notes))
<br><br>

### Context Manager Support

These semaphores support the context manager protocol so they can be used with Python's `with` statement, just like Python's `threading.Semaphore`. For instance --

```python
with posix_ipc.Semaphore(name) as sem:
    # Do something...
```

Entering the context acquires the semaphore, exiting the context releases the semaphore. See `demo4/child.py` for a complete example. The context manager only manages acquisition and release. If you create a new semaphore as part of executing the `with` statement, you must explicitly unlink it.

## The SharedMemory Class

This is a handle to a shared memory segment. POSIX shared memory segments masquerade as files, and so the handle to a shared memory segment is just a file descriptor that can be mmapped.

### Constructor

`SharedMemory(name, [flags = 0, [mode = 0600, [size = 0, [read_only = false]]]])`

Creates a new shared memory segment or opens an existing one.

*name* must be `None` or a string. If it is `None`, the module chooses a random unused name. If it is a string, it should begin with a slash and be valid according to pathname rules on your system, e.g. `/four_yorkshiremen_sharing_memories`

On some systems you need to have write access to the path.

The *flags* specify whether you want to create a new shared memory segment or open an existing one.

- With *flags* set to the default of `0`, the module attempts to open an existing segment and raises an error if that segment doesn't exist.
- With *flags* set to `O_CREAT`, the module opens the segment if it exists or creates it if it doesn't.
- With *flags* set to `O_CREAT | O_EXCL` (or `O_CREX`), the module creates a new shared memory segment identified by *name*. If a segment with that name already exists, the call raises an `ExistentialError`.

If you pass a non-zero size, the segment will be (re)sized accordingly, regardless of whether or not it's a new or existing segment. Prior to version 1.0.4, this documentation incorrectly stated that size was ignored if the segment already existed.

To (re)size the segment, `posix_ipc` calls `ftruncate()`. The same function is available to Python via [`os.ftruncate()`](https://docs.python.org/3/library/os.html#os.ftruncate). If you prefer to handle segment (re)sizing yourself, leave the `SharedMemory` parameter `size` at its default of `0` and call `os.ftruncate()` when and how you like.

Note that under macOS (up to and including 10.12 at least), you can only call `ftruncate()` once on a segment during its lifetime. This is a limitation of macOS, not `posix_ipc`.

When opening an existing shared memory segment, one can also specify the flag `O_TRUNC` to truncate the shared memory to zero bytes. macOS does not support `O_TRUNC`.

### Instance Methods

`close_fd()`

Closes the file descriptor associated with this SharedMemory object. Calling `close_fd()` is the same as calling [`os.close()`](hhttps://docs.python.org/3/library/os.html#os.close) on a SharedMemory object's `fd` attribute.

You must call `close_fd()` or `os.close()` explicitly; the file descriptor is **not** closed automatically when a SharedMemory object is garbage collected.

Closing the file descriptor has no effect on any `mmap` objects that were created from it. See the demo for an example.
<br><br>

`unlink()`

Marks the shared memory for destruction once all processes have unmapped it.

[The POSIX specification for `shm_unlink()`](http://www.opengroup.org/onlinepubs/009695399/functions/shm_unlink.html) says, "Even if the object continues to exist after the last shm_unlink(), reuse of the name shall subsequently cause shm_open() to behave as if no shared memory object of this name exists (that is, shm_open() will fail if O_CREAT is not set, or will create a new shared memory object if O_CREAT is set)."

I'll bet a virtual cup of coffee that this tricky part of the standard is not well or consistently implemented in every OS. Caveat emptor.

### Instance Attributes

`name` **(read-only)**

The name provided in the constructor.
<br><br>

`fd` **(read-only)**

The file descriptor that represents the memory segment.
<br><br>

`size` **(read-only)**

The size (in bytes) of the shared memory segment.

## The MessageQueue Class

This is a handle to a message queue.

### Constructor

`MessageQueue(name, [flags = 0, [mode = 0600, [max_messages = QUEUE_MESSAGES_MAX_DEFAULT, [max_message_size = QUEUE_MESSAGE_SIZE_MAX_DEFAULT, [read = True, [write = True]]]]]])`

Creates a new message queue or opens an existing one.*name* must be `None` or a string. If it is `None`, the module chooses a random unused name. If it is a string, it should begin with a slash and be valid according to pathname rules on your system, e.g. `/my_message_queue`
On some systems you need to have write access to the path.
The *flags* specify whether you want to create a new queue or open an existing one.

- With *flags* set to the default of `0`, the module attempts to open an existing queue and raises an error if that queue doesn't exist.
- With *flags* set to `O_CREAT`, the module opens the queue if it exists (in which case *size* and *mode* are ignored) or creates it if it doesn't.
- With *flags* set to `O_CREAT | O_EXCL` (or `O_CREX`), the module creates a new message queue identified by *name*. If a queue with that name already exists, the call raises an `ExistentialError`.

*Max_messages* defines how many messages can be in the queue at one time. When the queue is full, calls to `.send()` will wait.
*Max_message_size* defines the maximum size (in bytes) of a message.
*Read* and *write* default to True. If *read/write* is False, calling `.receive()/.send()` on this object is not permitted. This doesn't affect other handles to the same queue.

### Instance Methods

`send(message, [timeout = None, [priority = 0]])`

Sends a message via the queue.The *message* string can contain embedded NULLs (ASCII `0x00`). Under Python 3, the message can also be a bytes object.
The *timeout* (which can be a float) specifies how many seconds this call should wait if the queue is full. Timeouts are irrelevant when the `block` flag is False.

- A *timeout* of None (the default) implies no time limit. The call will not return until the message is sent.
- When *timeout* is 0, the call immediately raises a `BusyError` if asked to wait.
- When the *timeout* is > 0, the call will wait no longer than *timeout* seconds before either returning (having sent the message) or raising a `BusyError`.

The *priority* allows you to order messages in the queue. The highest priority message is received first. By default, messages are sent at the lowest priority (0).
<br><br>

`receive([timeout = None])`

Receives a message from the queue, returning a tuple of `(message, priority)`. Messages are received in the order of highest priority to lowest, and in FIFO order for messages of equal priority. Under Python 3, the returned message is a bytes object.
If the queue is empty, the call will not return immediately. The optional *timeout* parameter controls the wait just as for the function `send()`. It defaults to None.
<br><br>

`request_notification([notification = None])`

Depending on the parameter, requests or cancels notification from the operating system when the queue changes from empty to non-empty.

- When *notification* is not provided or `None`, any existing notification request is cancelled.
- When *notification* is an integer, notification will be sent as a signal of this value that can be caught using a signal handler installed with `signal.signal()`.
- When *notification* is a tuple of `(function, param)`, notification will be sent by invoking *`function(param)`* in a new thread.

Message queues accept only one notification request at a time. If another process has already requested notifications from this queue, this call will fail with a `BusyError`.
The operating system delivers (at most) one notification per request. If you want subsequent notifications, you must request them by calling `request_notification()` again.
<br><br>

`close()`

Closes this reference to the queue.You must call `close()` explicitly; it is **not** called automatically when a MessageQueue object is garbage collected.
<br><br>

`unlink()`

Requests destruction of the queue. Although the call returns immediately, actual destruction of the queue is postponed until all references to it are closed.

### Instance Attributes

`name` **(read-only)**

The name provided in the constructor.
<br><br>

`mqd` **(read-only)**

The message queue descriptor that represents the queue.
<br><br>

`block`

When True (the default), calls to `.send()` and `.receive()` may wait (block) if they cannot immediately satisfy the send/receive request. When `block` is False, the module will raise `BusyError` instead of waiting.
<br><br>

`max_messages` **(read-only)**

The maximum number of messages the queue can hold.
<br><br>

`max_message_size` **(read-only)**

The maximum message size (in bytes).
<br><br>

`current_messages` **(read-only)**

The number of messages currently in the queue.

## Usage Tips

### Tests

This module comes with fairly complete unit tests in the `tests` directory. To run them, install `posix_ipc` and then run this command from the same directory as `setup.py`:

```bash
python -m unittest discover
```

### Sample Code

This module comes with five sets of demonstration code, all [in the `demos` directory](https://github.com/osvenskan/posix_ipc/tree/develop/demos). The first (in the directory `demo1`) shows how to use shared memory and semaphores. The second (in the directory `demo2`) shows how to use message queues. The third (`demo3`) shows how to use message queue notifications. The fourth (`demo4`) shows how to use a semaphore in a context manager. The fifth (`demo5`) demonstrates use of message queues in combination with Python's `selectors` module.

### Nobody Likes a Mr. Messy

IPC objects are a little different from most Python objects and therefore require a little more care on the part of the programmer. When a program creates a IPC object, it creates something that resides *outside of its own process*, just like a file on a hard drive. It won't go away when your process ends unless you explicitly remove it. And since many operating systems don't even give you a way to enumerate existing POSIX IPC entities, it might be hard to figure out what you're leaving behind.

In short, remember to clean up after yourself.

### Semaphores and References

I know it's *verboten* to talk about pointers in Python, but I'm going to do it anyway.

Each Semaphore object created by this module contains a C pointer to the IPC object created by the system. When you call `sem.close()`, the object's internal pointer is set to `NULL`. This leaves the Python object in a not-quite-useless state. You can still call `sem.unlink()` or print `sem.name`, but calls to `sem.aquire()` or `sem.release()` will raise an `ExistentialError`.

If you know you're not going to use a Semaphore object after calling `sem.close()` or `sem.unlink()`, you could you set your semaphore variable to the return from the function (which is always `None`) like so:

```
    my_sem = my_sem.close()
```

That will ensure you don't have any nearly useless objects laying around that you might use by accident.

This doesn't apply to shared memory and message queues because they're referenced at the C level by a file descriptor rather than a pointer.

### Permissions

It appears that the read and write mode bits on IPC objects are ignored by the operating system. For instance, on macOS, OpenSolaris and Linux one can write to semaphores and message queues with a mode of `0400`.

### Message Queues

When creating a new message queue, you specify a maximum message size which defaults to `QUEUE_MESSAGE_SIZE_MAX_DEFAULT` (currently 8192 bytes). You can create a queue with a larger value, but be aware that `posix_ipc` allocates a buffer the size of the maximum message size every time `receive()` is called.

### Consult Your Local `man` Pages

The posix_ipc module is just a wrapper around your system's API. If your system's implementation has quirks, the `man` pages for `sem_open, sem_post, sem_wait, sem_close, sem_unlink, shm_open, shm_unlink, mq_open, mq_send mq_receive, mq_getattr, mq_close, mq_unlink`
and `mq_notify` will probably cover them.

### Last But Not Least

For Pythonistas, [a meditation on the inaccuracy of shared memories](https://www.youtube.com/watch?v=VKHFZBUTA4k)

## Known Bugs

I don't know of any bugs in this code, but FreeBSD users should check the platform notes.

## Support for Older Pythons

[Version 1.0.5 of `posix_ipc`](https://pypi.org/project/posix-ipc/1.0.5/) was the last to support both Python 2.7 and Python 3.x. No changes (neither fixes nor features) will be backported to 1.0.5.

If you need to support Python < 2.7, try [posix_ipc version 0.9.9](https://pypi.org/project/posix-ipc/0.9.9/).

# Platform Notes

This module is just a wrapper around the operating system's functions, so if the operating system doesn't provide a function, this module can't either. The POSIX Realtime Extensions (POSIX 1003.1b-1993) are, as the name implies, an extension to POSIX and so a platform can claim "*POSIX conformance*" and still not support any or all of the IPC functions.

**Linux with kernel ≥ 2.6**

All features supported.

**OpenSolaris ≥ 2008.05**

All features supported.

**FreeBSD ≥ 7.2**

All features supported.Under 7.2, `posix_ipc`'s demos fail unless they're run as root. It's a simple permissions problem. Prefix the IPC object names with `/tmp` in `params.txt` and the problem goes away. I didn't see this behavior under FreeBSD 8.0, so it must have been fixed at some point.
If you don't have the `sem` and `mqueuefs` kernel modules loaded, you'll get a message like this (or something similarly discouraging) when you try to create a semaphore or message queue:`Bad system call: 12 (core dumped)`
Type `kldstat` to list loaded modules, and `kldload sem` or `kldload mqueuefs` if you need to load either of these. BTW, [mqueuefs](http://www.freebsd.org/cgi/man.cgi?query=mqueuefs&apropos=0&sektion=5&manpath=FreeBSD+8.0-stable&format=html) has some cool features.
Prior to 7.2, FreeBSD POSIX semaphore support was [broken](http://www.freebsd.org/cgi/query-pr.cgi?pr=127545).
Under FreeBSD 11.1, I have seen segfaults during the message queue threaded notification rearm test. I don't know if `posix_ipc` or FreeBSD (or both!) are culprits.

**macOS/OS X (up to and including 15.4)**

macOS' implementation of POSIX IPC has some significant holes. Message queues are not supported at all. Also, `sem_getvalue()` and `sem_timedwait()` are not supported.

**Windows + Cygwin 1.7**

[Cygwin](http://www.cygwin.com/) is a Linux-like environment for Windows.
Versions of Cygwin prior to 1.7 didn't support POSIX IPC. Under Cygwin 1.7 beta 62 (released in early October 2009), `posix_ipc` compiles and runs both demos.
