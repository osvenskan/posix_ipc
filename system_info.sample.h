/*
This is a sample version of system_info.h. See building.md for more information
about why you might find it interesting.

In addition to the values documented below, you can also add this one --

#define POSIX_IPC_DEBUG

Doing so will cause posix_ipc to print messages to stderr as it runs. Use this
with care; it's a developer-only feature and the implementation isn't very
robust.
*/

/* POSIX_IPC_VERSION should be a quoted string. It's what the module will
report in its VERSION and __version__ attributes.
*/
#define POSIX_IPC_VERSION "1.2.0"

/* PAGE_SIZE is the size (in bytes) of a block of memory. When allocating
shared memory, some systems will round odd sizes up to the next PAGE_SIZE
unit. (e.g. if PAGE_SIZE is 16384, a block that is nominally 10k would still
occupy 16k of shared memory.)

You should be able to get this value via Python using this command --

    python -c "import os; print(os.sysconf('SC_PAGE_SIZE'))"

This value only provides information to module users. The module reports it as
posix_ipc.PAGE_SIZE, but that value isn't used anywhere in the module code,
so if it's wrong, that might not matter to you.

PAGE_SIZE is already #defined in system header files on many systems, so
it should be surrounded with #ifndef/#endif here.
*/
#ifndef PAGE_SIZE
#define PAGE_SIZE                       16384
#endif

/* MESSAGE_QUEUE_SUPPORT_EXISTS should be #defined if and only if the host OS
supports message queues. (They're not supported on Mac.) If this is not
#defined in this file, message queue support will not be available in
the compiled module.
*/
#define MESSAGE_QUEUE_SUPPORT_EXISTS

/* QUEUE_MESSAGES_MAX_DEFAULT is the default value for the max number of
messages in a MessageQueue. It's only used if the caller doesn't supply a
value when creating an instance.
*/
#define QUEUE_MESSAGES_MAX_DEFAULT      10

/* QUEUE_MESSAGE_SIZE_MAX_DEFAULT is the default value for the max size
(in bytes) of messages in a MessageQueue. It's only used if the caller doesn't
supply a value when creating an instance.
*/
#define QUEUE_MESSAGE_SIZE_MAX_DEFAULT  8192

/* QUEUE_PRIORITY_MAX defines the (0-based) upper bound of message
priorities. 31 is the minimum allowable value for POSIX compliance. Some
systems allow much higher values (e.g. 32768).

You should be able to get this value via Python using this command --

    python -c "import os; print(os.sysconf('SC_MQ_PRIO_MAX'))"

This is an unsigned int, so in this file it must be followed by the letter U.

This value is enforced by posix_ipc. If you try to send a message with a
priority > QUEUE_PRIORITY_MAX, posix_ipc will raise an exception.
*/
#define QUEUE_PRIORITY_MAX              31U

/* SEM_GETVALUE_EXISTS should be #defined if and only if the host OS supports
sem_getvalue(). When sem_getvalue() is implemented, posix_ipc enables
the `value` attribute on Semaphore instances. (It's not supported on Mac.)
*/
#define SEM_GETVALUE_EXISTS

/* SEM_TIMEDWAIT_EXISTS should be #defined if and only if the host OS supports
sem_timedwait(). When sem_timedwait() is implemented, posix_ipc enables
non-infinite timeouts for acquire() on Semaphore instances.
(It's not supported on Mac.)
*/
#define SEM_TIMEDWAIT_EXISTS

/* SEM_VALUE_MAX is the maximum value of a semaphore.

This value only provides information to module users. The module reports it as
posix_ipc.SEMAPHORE_VALUE_MAX, but that value isn't used anywhere in the
module code, so if it's wrong, that might not matter to you.

SEM_VALUE_MAX is already #defined in system header files on many systems, so
it should be surrounded with #ifndef/#endif here.
*/
#ifndef SEM_VALUE_MAX
#define SEM_VALUE_MAX                   32767
#endif
