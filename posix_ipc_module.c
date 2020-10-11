/*
posix_ipc - A Python module for accessing POSIX 1003.1b-1993 semaphores,
            shared memory and message queues.

Copyright (c) 2018, Philip Semanchuk
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of posix_ipc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY ITS CONTRIBUTORS ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL Philip Semanchuk BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include "structmember.h"

#include <time.h>
#include <sys/time.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>

// Just for the math surrounding timeouts for sem_timedwait()
#include <math.h>

// For mq_notify
#include <signal.h>
#include <pthread.h>

#include "probe_results.h"

// For semaphore stuff
#include <semaphore.h>

// For shared memory stuff
#include <sys/stat.h>
#include <sys/mman.h>

#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
// For msg queues
#include <mqueue.h>
#endif

/* POSIX says that a mode_t "shall be an integer type". To avoid the need
for a specific get_mode function for each type, I'll just stuff the mode into
a long and mention it in the Xxx_members list for each type.
ref: http://www.opengroup.org/onlinepubs/000095399/basedefs/sys/types.h.html
*/

typedef struct {
    PyObject_HEAD
    char *name;
    long mode;
    sem_t *pSemaphore;
} Semaphore;


typedef struct {
    PyObject_HEAD
    char *name;
    long mode;
    int fd;
} SharedMemory;


#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
typedef struct {
    PyObject_HEAD
    char *name;
    mqd_t mqd;
    long mode;
    long max_messages;
    long max_message_size;
    int send_permitted;
    int receive_permitted;
    PyObject *notification_callback;
    PyObject *notification_callback_param;
    // In the event that the user requests notifications in a new thread,
    // I'll need a reference to the interpreter in order to create the
    // thread for the callback. See request_notification() and
    // process_notification() for details.
    PyInterpreterState *interpreter;
} MessageQueue;
#endif

// FreeBSD (and perhaps other BSDs) limit names to 14 characters. In the
// code below, strings of this length are allocated on the stack, so
// increase this gently or change that code to use malloc().
#define MAX_SAFE_NAME_LENGTH  14

// POSIX_IPC_SHM_NO_VALUE is the placeholder value for SharedMemory file descriptors that are
// uninitialized, closed, or otherwise not useful. It cannot have a value other than -1 because
// it's used interchangeably with the shm_open() failure return code (which is -1).
// ref: http://pubs.opengroup.org/onlinepubs/009695399/functions/shm_open.html
// ref: https://github.com/osvenskan/posix_ipc/issues/2
#define POSIX_IPC_SHM_NO_VALUE         -1

// POSIX_IPC_MQ_NO_VALUE is the same concept as POSIX_IPC_SHM_NO_VALUE, but for message queues.
// However, while POSIX_IPC_SHM_NO_VALUE is a necessity, this is just defensive programming.
// In my experience, all systems on which message queues are implemented use pointers (rather than
// file descriptors) for message queue handles, so both 0 and -1 could serve to represent
// an uninitialized handle. -1 is a better choice, though, in case some future system uses
// file handles, and to keep my message queue implementation consistent with my shared mem and
// semaphore implementations.
#define POSIX_IPC_MQ_NO_VALUE    (mqd_t)-1

/* Struct to contain a timeout which can be None */
typedef struct {
    int is_none;
    int is_zero;
    struct timespec timestamp;
} NoneableTimeout;


/* Struct to contain an IPC object name which can be None */
typedef struct {
    int is_none;
    char *name;
} NoneableName;


/*
      Exceptions for this module
*/

static PyObject *pBaseException;
static PyObject *pPermissionsException;
static PyObject *pSignalException;
static PyObject *pExistentialException;
static PyObject *pBusyException;


#define ONE_BILLION 1000000000

#ifdef POSIX_IPC_DEBUG
#define DPRINTF(fmt, args...) fprintf(stderr, "+++ " fmt, ## args)
#else
#define DPRINTF(fmt, args...)
#endif

#if PY_MAJOR_VERSION > 2
static char *
bytes_to_c_string(PyObject* o, int lock) {
/* Convert a bytes object to a char *. Optionally lock the buffer if it is a
   bytes array.
   This code swiped directly from Python 3.1's posixmodule.c by Yours Truly.
   The name there is bytes2str().
*/
    if (PyBytes_Check(o))
        return PyBytes_AsString(o);
    else if (PyByteArray_Check(o)) {
        if (lock && PyObject_GetBuffer(o, NULL, 0) < 0)
            /* On a bytearray, this should not fail. */
            PyErr_BadInternalCall();
        return PyByteArray_AsString(o);
    } else {
        /* The FS converter should have verified that this
           is either bytes or bytearray. */
        Py_FatalError("bad object passed to bytes2str");
        /* not reached. */
        return "";
    }
}

static void
release_bytes(PyObject* o)
    /* Release the lock, decref the object.
   This code swiped directly from Python 3.1's posixmodule.c by Yours Truly.
   */
{
    if (PyByteArray_Check(o))
        o->ob_type->tp_as_buffer->bf_releasebuffer(NULL, 0);
    Py_DECREF(o);
}
#endif


static int
random_in_range(int min, int max) {
    // returns a random int N such that min <= N <= max
    int diff = (max - min) + 1;

    // ref: http://www.c-faq.com/lib/randrange.html
    return ((int)((double)rand() / ((double)RAND_MAX + 1) * diff)) + min;
}


static
int create_random_name(char *name) {
    // The random name is always lowercase so that this code will work
    // on case-insensitive file systems. It always starts with a forward
    // slash.
    int length;
    char *alphabet = "abcdefghijklmnopqrstuvwxyz";
    int i;

    // Generate a random length for the name. I subtract 1 from the
    // MAX_SAFE_NAME_LENGTH in order to allow for the name's leading "/".
    length = random_in_range(6, MAX_SAFE_NAME_LENGTH - 1);

    name[0] = '/';
    name[length] = '\0';
    i = length;
    while (--i)
        name[i] = alphabet[random_in_range(0, 25)];

    return length;
}


static int
convert_name_param(PyObject *py_name_param, void *checked_name) {
    /* Verifies that the py_name_param is either None or a string.
    If it's a string, checked_name->name points to a PyMalloc-ed buffer
    holding a NULL-terminated C version of the string when this function
    concludes. The caller is responsible for releasing the buffer.
    */
    int rc = 0;
    NoneableName *p_name = (NoneableName *)checked_name;
#if PY_MAJOR_VERSION > 2
    PyObject *py_name_as_bytes = NULL;
    char *p_name_as_c_string = NULL;
#endif

    DPRINTF("inside convert_name_param\n");
    DPRINTF("PyBytes_Check() = %d \n", PyBytes_Check(py_name_param));
#if PY_MAJOR_VERSION < 3
    DPRINTF("PyString_Check() = %d \n", PyString_Check(py_name_param));
#endif
    DPRINTF("PyUnicode_Check() = %d \n", PyUnicode_Check(py_name_param));

    p_name->is_none = 0;

    // The name can be None or a Python string
    if (py_name_param == Py_None) {
        DPRINTF("name is None\n");
        rc = 1;
        p_name->is_none = 1;
    }
#if PY_MAJOR_VERSION > 2
    else if (PyUnicode_Check(py_name_param) || PyBytes_Check(py_name_param)) {
        DPRINTF("name is Unicode or bytes\n");
        // The caller passed me a Unicode string or a byte array; I need a
        // char *. Getting from one to the other takes a couple steps.

        if (PyUnicode_Check(py_name_param)) {
            DPRINTF("name is Unicode\n");
            // PyUnicode_FSConverter() converts the Unicode object into a
            // bytes or a bytearray object. (Why can't it be one or the other?)
            PyUnicode_FSConverter(py_name_param, &py_name_as_bytes);
        }
        else {
            DPRINTF("name is bytes\n");
            // Make a copy of the name param.
            py_name_as_bytes = PyBytes_FromObject(py_name_param);
        }

        // bytes_to_c_string() returns a pointer to the buffer.
        p_name_as_c_string = bytes_to_c_string(py_name_as_bytes, 0);

        // PyMalloc memory and copy the user-supplied name to it.
        p_name->name = (char *)PyMem_Malloc(strlen(p_name_as_c_string) + 1);
        if (p_name->name) {
            rc = 1;
            strcpy(p_name->name, p_name_as_c_string);
        }
        else
            PyErr_SetString(PyExc_MemoryError, "Out of memory");

        // The bytes version of the name isn't useful to me, and per the
        // documentation for PyUnicode_FSConverter(), I am responsible for
        // releasing it when I'm done.
        release_bytes(py_name_as_bytes);
    }
#else
    else if (PyString_Check(py_name_param) || PyUnicode_Check(py_name_param)) {
        DPRINTF("name is string or unicode\n");
        // PyMalloc memory and copy the user-supplied name to it.
        p_name->name = (char *)PyMem_Malloc(PyString_Size(py_name_param) + 1);
        if (p_name->name) {
            rc = 1;
            strcpy(p_name->name, PyString_AsString(py_name_param));
        }
        else
            PyErr_SetString(PyExc_MemoryError, "Out of memory");
    }
#endif
    else
        PyErr_SetString(PyExc_TypeError, "Name must be None or a string");

    return rc;
}


static
int convert_timeout(PyObject *py_timeout, void *converted_timeout) {
    // Converts a PyObject into a timeout if possible. The PyObject should
    // be None or some sort of numeric value (e.g. int, float, etc.)
    // converted_timeout should point to a NoneableTimeout. When this function
    // returns, if the NoneableTimeout's is_none is true, then the rest of the
    // struct is undefined. Otherwise, the rest of the struct is populated.
    int rc = 0;
    double simple_timeout = 0;
    struct timeval current_time;
    NoneableTimeout *p_timeout = (NoneableTimeout *)converted_timeout;

    // The timeout can be None or any Python numeric type (float,
    // int, long).
    if (py_timeout == Py_None)
        rc = 1;
    else if (PyFloat_Check(py_timeout)) {
        rc = 1;
        simple_timeout = PyFloat_AsDouble(py_timeout);
    }
#if PY_MAJOR_VERSION < 3
    else if (PyInt_Check(py_timeout)) {
        rc = 1;
        simple_timeout = (double)PyInt_AsLong(py_timeout);
    }
#endif
    else if (PyLong_Check(py_timeout)) {
        rc = 1;
        simple_timeout = (double)PyLong_AsLong(py_timeout);
    }

    // The timeout may not be negative.
    if ((rc) && (simple_timeout < 0))
        rc = 0;

    if (!rc)
        PyErr_SetString(PyExc_TypeError,
                        "The timeout must be None or a non-negative number");
    else {
        if (py_timeout == Py_None)
            p_timeout->is_none = 1;
        else {
            p_timeout->is_none = 0;

            p_timeout->is_zero = (!simple_timeout);

            gettimeofday(&current_time, NULL);

            simple_timeout += current_time.tv_sec;
            simple_timeout += (float)current_time.tv_usec / 1e6;

            p_timeout->timestamp.tv_sec = (time_t)floor(simple_timeout);
            p_timeout->timestamp.tv_nsec = (long)((simple_timeout - floor(simple_timeout)) * ONE_BILLION);
        }
    }

    return rc;
}

static PyObject *
generic_str(char *name) {
#if PY_MAJOR_VERSION > 2
    return PyUnicode_FromString(name ? name : "(no name)");
#else
    return PyString_FromString(name ? name : "(no name)");
#endif
}

static void
mode_to_str(long mode, char *mode_str) {
    // Given a numeric mode and preallocated string space, populates the
    // string with the mode formatted as an octal number.
    sprintf(mode_str, "0%o", (int)mode);
}


static int test_semaphore_validity(Semaphore *p) {
    // Returns 1 (true) if the Semaphore object refers to a valid
    // semaphore, 0 (false) otherwise. In the latter case, it sets the
    // Python exception info and the caller should immediately return NULL.
    // The false condition should not arise unless the user of the module
    // tries to use a Semaphore after it's been closed.
    int valid = 1;

    if (SEM_FAILED == p->pSemaphore) {
        valid = 0;
        PyErr_SetString(pExistentialException, "The semaphore has been closed");
    }

    return valid;
}

/*   =====  Semaphore implementation functions =====   */

static PyObject *
sem_str(Semaphore *self) {
    return generic_str(self->name);
}


static PyObject *
sem_repr(Semaphore *self) {
    char mode[32];

    mode_to_str(self->mode, mode);

#if PY_MAJOR_VERSION > 2
    return PyUnicode_FromFormat("posix_ipc.Semaphore(\"%s\", mode=%s)",
                                self->name, mode);
#else
    return PyString_FromFormat("posix_ipc.Semaphore(\"%s\", mode=%s)",
                                self->name, mode);
#endif
}


static PyObject *
my_sem_unlink(const char *name) {
    DPRINTF("unlinking sem name %s\n", name);
    if (-1 == sem_unlink(name)) {
        switch (errno) {
            case EACCES:
                PyErr_SetString(pPermissionsException,
                                "Denied permission to unlink this semaphore");
            break;

            case ENOENT:
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "No semaphore exists with the specified name");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError, "The name is too long");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static void
Semaphore_dealloc(Semaphore *self) {
    /* Note -- I make no attempt to close the semaphore because that
       kills access to the semaphore for every thread in this process,
       which would make multi-threaded programming difficult.
    */
    DPRINTF("dealloc\n");
    PyMem_Free(self->name);
    self->name = NULL;

    Py_TYPE(self)->tp_free((PyObject*)self);
}


static PyObject *
Semaphore_new(PyTypeObject *type, PyObject *args, PyObject *kwlist) {
    Semaphore *self;

    self = (Semaphore *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


static int
Semaphore_init(Semaphore *self, PyObject *args, PyObject *keywords) {
    NoneableName name;
    char temp_name[MAX_SAFE_NAME_LENGTH + 1];
    unsigned int initial_value = 0;
    int flags = 0;
    static char *keyword_list[ ] = {"name", "flags", "mode", "initial_value", NULL};

    // First things first -- initialize the self struct. I use SEM_FAILED to represent
    // an uninitialized pointer to a semaphore because at least one platform (OS X) uses
    // file handles to represent semaphore handles, and they can be 0. See comments here --
    // https://github.com/osvenskan/posix_ipc/issues/2
    self->pSemaphore = SEM_FAILED;
    self->name = NULL;
    self->mode = 0600;

    // Semaphore(name, [flags = 0, [mode = 0600, [initial_value = 0]]])

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O&|iiI", keyword_list,
                                    &convert_name_param, &name, &flags,
                                    &(self->mode), &initial_value))
        goto error_return;


    if ( !(flags & O_CREAT) && (flags & O_EXCL) ) {
        PyErr_SetString(PyExc_ValueError,
                "O_EXCL must be combined with O_CREAT");
        goto error_return;
    }

    if (name.is_none && ((flags & O_EXCL) != O_EXCL)) {
        PyErr_SetString(PyExc_ValueError,
                "Name can only be None if O_EXCL is set");
        goto error_return;
    }

    if (name.is_none) {
        // (name == None) ==> generate a name for the caller
        do {
            errno = 0;
            create_random_name(temp_name);

            DPRINTF("Calling sem_open, name=%s, flags=0x%x, mode=0%o, initial value=%d\n",
                    temp_name, flags, (int)self->mode, initial_value);
            self->pSemaphore = sem_open(temp_name, flags, (mode_t)self->mode,
                                        initial_value);

        } while ( (SEM_FAILED == self->pSemaphore) && (EEXIST == errno) );

        // PyMalloc memory and copy the randomly-generated name to it.
        self->name = (char *)PyMem_Malloc(strlen(temp_name) + 1);
        if (self->name)
            strcpy(self->name, temp_name);
        else {
            PyErr_SetString(PyExc_MemoryError, "Out of memory");
            goto error_return;
        }
    }
    else {
        // (name != None) ==> use name supplied by the caller. It was
        // already converted to C by convert_name_param().
        self->name = name.name;

        DPRINTF("Calling sem_open, name=%s, flags=0x%x, mode=0%o, initial value=%d\n",
                self->name, flags, (int)self->mode, initial_value);
        self->pSemaphore = sem_open(self->name, flags, (mode_t)self->mode,
                                    initial_value);
    }

    DPRINTF("pSemaphore == %p\n", self->pSemaphore);

    if (self->pSemaphore == SEM_FAILED) {
        switch (errno) {
            case EACCES:
                PyErr_SetString(pPermissionsException,
                                "Permission denied");
            break;

            case EEXIST:
                PyErr_SetString(pExistentialException,
                    "A semaphore with the specified name already exists");
            break;

            case ENOENT:
                PyErr_SetString(pExistentialException,
                    "No semaphore exists with the specified name");
            break;

            case EINVAL:
                PyErr_SetString(PyExc_ValueError, "Invalid parameter(s)");
            break;

            case EMFILE:
                PyErr_SetString(PyExc_OSError,
                    "This process already has the maximum number of files open");
            break;

            case ENFILE:
                PyErr_SetString(PyExc_OSError,
                    "The system limit on the total number of open files has been reached");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError, "The name is too long");
            break;

            case ENOMEM:
                PyErr_SetString(PyExc_MemoryError, "Not enough memory");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }
    // else
        // all is well, nothing to do

    return 0;

    error_return:
    return -1;
}


static PyObject *
Semaphore_release(Semaphore *self) {
    if (!test_semaphore_validity(self))
        goto error_return;

    if (-1 == sem_post(self->pSemaphore)) {
        switch (errno) {
            case EINVAL:
            case EBADF:
                PyErr_SetString(pExistentialException,
                                "The semaphore does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static PyObject *
Semaphore_acquire(Semaphore *self, PyObject *args, PyObject *keywords) {
    NoneableTimeout timeout;
    int rc = 0;
    static char *keyword_list[] = {"timeout", NULL};

    if (!test_semaphore_validity(self))
        goto error_return;

    // Initialize this to the default of None.
    timeout.is_none = 1;

    // acquire([timeout=None])

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "|O&", keyword_list,
                                     convert_timeout, &timeout))
        goto error_return;

    Py_BEGIN_ALLOW_THREADS
    // timeout == None: no timeout, i.e. wait forever.
    // timeout == 0: raise an error if a wait would occur.
    // timeout  > 0: wait no longer than t seconds before raising an error.
    if (timeout.is_none) {
        DPRINTF("calling sem_wait()\n");
        rc = sem_wait(self->pSemaphore);
    }
    else {
        // Timeout is not None (i.e. is numeric)
        // A simple_timeout of zero implies the same behavior as
        // sem_trywait() so I call that instead. Doing so makes it easier
        // to ensure this code behaves consistently regardless of whether
        // or not sem_timedwait() is available.
        if (timeout.is_zero) {
            DPRINTF("calling sem_trywait()\n");
            rc = sem_trywait(self->pSemaphore);
        }
        else {
            // timeout is not None and is > 0.0
            // sem_timedwait isn't available on all systems. Where it's not
            // available I call sem_wait() instead.
#ifdef SEM_TIMEDWAIT_EXISTS
            DPRINTF("calling sem_timedwait()\n");
            DPRINTF("timeout tv_sec = %ld; timeout tv_nsec = %ld\n",
                    timeout.timestamp.tv_sec, timeout.timestamp.tv_nsec);

            rc = sem_timedwait(self->pSemaphore, &(timeout.timestamp));
#else
            DPRINTF("calling sem_wait()\n");
            rc = sem_wait(self->pSemaphore);
#endif
        }
    }
    Py_END_ALLOW_THREADS

    if (-1 == rc) {
        DPRINTF("sem_wait() rc = %d, errno = %d\n", rc, errno);

        switch (errno) {
            case EBADF:
            case EINVAL:
                // Linux documentation says that EINVAL has two meanings --
                // 1) self->pSemaphore no longer points to a valid semaphore
                // 2) timeout is < 0 or > one billion.
                // Since my code above guards against out-of-range
                // timeout values, I expect the second condition is
                // impossible here.
                PyErr_SetString(pExistentialException,
                                "The semaphore does not exist");
            break;

            case EINTR:
                /* If the signal was generated by Ctrl-C, calling
                PyErr_CheckSignals() here has the side effect of setting
                Python's error indicator. Otherwise there's a good chance
                it won't be set.
                http://groups.google.com/group/comp.lang.python/browse_thread/thread/ada39e984dfc3da6/fd6becbdce91a6be?#fd6becbdce91a6be
                */
                PyErr_CheckSignals();

                if (!(PyErr_Occurred() &&
                      PyErr_ExceptionMatches(PyExc_KeyboardInterrupt))
                   ) {
                    PyErr_Clear();
                    PyErr_SetString(pSignalException,
                                    "The wait was interrupted by a signal");
                }
                // else
                    // If KeyboardInterrupt error is set, I propogate that
                    // up to the caller.
            break;

            case EAGAIN:
            case ETIMEDOUT:
                PyErr_SetString(pBusyException,
                                "Semaphore is busy");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


// sem_getvalue isn't available on all systems.
#ifdef SEM_GETVALUE_EXISTS
static PyObject *
Semaphore_getvalue(Semaphore *self, void *closure) {
    int value;

    if (!test_semaphore_validity(self))
        goto error_return;

    if (-1 == sem_getvalue(self->pSemaphore, &value)) {
        switch (errno) {
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "The semaphore does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }

    return Py_BuildValue("i", value);

    error_return:
    return NULL;
}
// end #ifdef SEM_GETVALUE_EXISTS
#endif


static PyObject *
Semaphore_unlink(Semaphore *self) {
    if (!test_semaphore_validity(self))
        goto error_return;

    return my_sem_unlink(self->name);

    error_return:
    return NULL;
}


static PyObject *
Semaphore_close(Semaphore *self) {
    if (!test_semaphore_validity(self))
        goto error_return;

    if (-1 == sem_close(self->pSemaphore)) {
        switch (errno) {
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "The semaphore does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }
    else
        self->pSemaphore = NULL;

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static PyObject *
Semaphore_enter(Semaphore *self) {
    PyObject *args = PyTuple_New(0);
    PyObject *retval = NULL;

    if (Semaphore_acquire(self, args, NULL)) {
        retval = (PyObject *)self;
        Py_INCREF(self);
    }
    /* else acquisition failed for some reason so just fall through to
       the return statement below and return NULL. Semaphore_acquire() has
       already called PyErr_SetString() to set the relevant error.
    */

    Py_DECREF(args);

    return retval;
}


static PyObject *
Semaphore_exit(Semaphore *self, PyObject *args) {
    DPRINTF("exiting context and releasing semaphore %s\n", self->name);
    return Semaphore_release(self);
}

/*   =====  End Semaphore functions  =====                  */




/*   =====  Begin Shared Memory implementation functions ===== */

static PyObject *
shm_str(SharedMemory *self) {
    return generic_str(self->name);
}

static PyObject *
shm_repr(SharedMemory *self) {
    char mode[32];

    mode_to_str(self->mode, mode);

#if PY_MAJOR_VERSION > 2
    return PyUnicode_FromFormat("posix_ipc.SharedMemory(\"%s\", mode=%s)",
                                self->name, mode);
#else
    return PyString_FromFormat("posix_ipc.SharedMemory(\"%s\", mode=%s)",
                                self->name, mode);
#endif
}

static PyObject *
my_shm_unlink(const char *name) {
    DPRINTF("unlinking shm name %s\n", name);
    if (-1 == shm_unlink(name)) {
        switch (errno) {
            case EACCES:
                PyErr_SetString(pPermissionsException, "Permission denied");
            break;

            case ENOENT:
                PyErr_SetString(pExistentialException,
                    "No shared memory exists with the specified name");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError, "The name is too long");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static PyObject *
SharedMemory_new(PyTypeObject *type, PyObject *args, PyObject *kwlist) {
    SharedMemory *self;

    self = (SharedMemory *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


static int
SharedMemory_init(SharedMemory *self, PyObject *args, PyObject *keywords) {
    NoneableName name;
    char temp_name[MAX_SAFE_NAME_LENGTH + 1];
    unsigned int flags = 0;
    unsigned long size = 0;
    int read_only = 0;
    static char *keyword_list[ ] = {"name", "flags", "mode", "size", "read_only", NULL};

    // First things first -- initialize the self struct.
    self->name = NULL;
    self->fd = POSIX_IPC_SHM_NO_VALUE;
    self->mode = 0600;

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O&|Iiki", keyword_list,
                                    &convert_name_param, &name, &flags,
                                    &(self->mode), &size, &read_only))
        goto error_return;

    if ( !(flags & O_CREAT) && (flags & O_EXCL) ) {
        PyErr_SetString(PyExc_ValueError,
                "O_EXCL must be combined with O_CREAT");
        goto error_return;
    }

    if (name.is_none && ((flags & O_EXCL) != O_EXCL)) {
        PyErr_SetString(PyExc_ValueError,
                "Name can only be None if O_EXCL is set");
        goto error_return;
    }

    flags |= (read_only ? O_RDONLY : O_RDWR);

    if (name.is_none) {
        // (name == None) ==> generate a name for the caller
        do {
            errno = 0;
            create_random_name(temp_name);

            DPRINTF("calling shm_open, name=%s, flags=0x%x, mode=0%o\n",
                        temp_name, flags, (int)self->mode);
            self->fd = shm_open(temp_name, flags, (mode_t)self->mode);

        } while ( (-1 == self->fd) && (EEXIST == errno) );

        // PyMalloc memory and copy the randomly-generated name to it.
        self->name = (char *)PyMem_Malloc(strlen(temp_name) + 1);
        if (self->name)
            strcpy(self->name, temp_name);
        else {
            PyErr_SetString(PyExc_MemoryError, "Out of memory");
            goto error_return;
        }
    }
    else {
        // (name != None) ==> use name supplied by the caller. It was
        // already converted to C by convert_name_param().
        self->name = name.name;

        DPRINTF("calling shm_open, name=%s, flags=0x%x, mode=0%o\n",
                    self->name, flags, (int)self->mode);
        self->fd = shm_open(self->name, flags, (mode_t)self->mode);
    }

    DPRINTF("shm fd = %d\n", self->fd);

    if (-1 == self->fd) {
        switch (errno) {
            case EACCES:
                PyErr_Format(pPermissionsException,
                                "No permission to %s this segment",
                                (flags & O_TRUNC) ? "truncate" : "access"
                                );
            break;

            case EEXIST:
                PyErr_SetString(pExistentialException,
                                "Shared memory with the specified name already exists");
            break;

            case ENOENT:
                PyErr_SetString(pExistentialException,
                                "No shared memory exists with the specified name");
            break;

            case EINVAL:
                PyErr_SetString(PyExc_ValueError, "Invalid parameter(s)");
            break;

            case EMFILE:
                PyErr_SetString(PyExc_OSError,
                                 "This process already has the maximum number of files open");
            break;

            case ENFILE:
                PyErr_SetString(PyExc_OSError,
                                 "The system limit on the total number of open files has been reached");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError,
                                 "The name is too long");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }
    else {
        if (size) {
            DPRINTF("calling ftruncate, fd = %d, size = %ld\n", self->fd, size);
            if (-1 == ftruncate(self->fd, (off_t)size)) {
                // The code below will raise a Python error. Since that error
                // is raised during __init__(), it will look to the caller
                // as if object creation failed entirely. Here I clean up
                // the system object I just created.
                close(self->fd);
                shm_unlink(self->name);

                // ftruncate can return a ton of different errors, but most
                // are not relevant or are extremely unlikely.
                switch (errno) {
                    case EINVAL:
                        PyErr_SetString(PyExc_ValueError,
                                        "The size is invalid or the memory is read-only");
                    break;

                    case EFBIG:
                        PyErr_SetString(PyExc_ValueError,
                                        "The size is too large");
                    break;

                    case EROFS:
                    case EACCES:
                        PyErr_SetString(pPermissionsException,
                                        "The memory is read-only");
                    break;

                    default:
                        PyErr_SetFromErrno(PyExc_OSError);
                    break;
                }

                goto error_return;
            }
        }
    }

    return 0;

    error_return:
    return -1;
}


static void SharedMemory_dealloc(SharedMemory *self) {
    DPRINTF("dealloc\n");
    PyMem_Free(self->name);
    self->name = NULL;

    Py_TYPE(self)->tp_free((PyObject*)self);
}


PyObject *
SharedMemory_getsize(SharedMemory *self, void *closure) {
    struct stat fileinfo;
    off_t size = -1;

    if (0 == fstat(self->fd, &fileinfo))
        size = fileinfo.st_size;
    else {
        switch (errno) {
            case EBADF:
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "The segment does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    return Py_BuildValue("k", (unsigned long)size);

    error_return:
    return NULL;
}


PyObject *
SharedMemory_fileno(SharedMemory *self) {
#if PY_MAJOR_VERSION > 2
    return PyLong_FromLong((long)self->fd);
#else
    return PyInt_FromLong((long)self->fd);
#endif
}


PyObject *
SharedMemory_close_fd(SharedMemory *self) {
    if (POSIX_IPC_SHM_NO_VALUE != self->fd) {
        DPRINTF("SharedMemory_close_fd, fd=%d\n", self->fd);
        if (-1 == close(self->fd)) {
            DPRINTF("SharedMemory_close_fd, close failed\n");
            switch (errno) {
                case EBADF:
                    PyErr_SetString(PyExc_ValueError,
                                    "The file descriptor is invalid");
                break;

                default:
                    PyErr_SetFromErrno(PyExc_OSError);
                break;
            }

            goto error_return;
        }
        else {
            // Close was successful so the fd is no longer valid.
            self->fd = POSIX_IPC_SHM_NO_VALUE;
        }
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


PyObject *
SharedMemory_unlink(SharedMemory *self) {
    return my_shm_unlink(self->name);
}


/*   =====  End Shared Memory functions =====           */


/*   =====  Begin Message Queue implementation functions ===== */

#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS

static PyObject *
mq_str(MessageQueue *self) {
    return generic_str(self->name);
}

static PyObject *
mq_repr(MessageQueue *self) {
    char mode[32];
    char read[32];
    char write[32];

    strcpy(read, self->receive_permitted ? "True" : "False");
    strcpy(write, self->send_permitted ? "True" : "False");
    mode_to_str(self->mode, mode);

#if PY_MAJOR_VERSION > 2
    return PyUnicode_FromFormat("posix_ipc.MessageQueue(\"%s\", mode=%s, max_message_size=%ld, max_messages=%ld, read=%s, write=%s)",
                self->name, mode, self->max_message_size, self->max_messages,
                read, write);
#else
    return PyString_FromFormat("posix_ipc.MessageQueue(\"%s\", mode=%s, max_message_size=%ld, max_messages=%ld, read=%s, write=%s)",
                self->name, mode, self->max_message_size, self->max_messages,
                read, write);
#endif
}


void
mq_cancel_notification(MessageQueue *self) {
    // Based on the documentation, mq_notify() can only fail in this context
    // if mqd is invalid. That will only occur if the queue has been
    // destroyed, in which case notifications are effectively cancelled
    // anyway. Therefore I don't care about the return code from mq_notify()
    // and this function is always successful.

    // I hope this doesn't come back to bite me...
    int rc;

    rc = mq_notify(self->mqd, NULL);
    DPRINTF("Notification cancelled, rc=%d\n", rc);

    Py_XDECREF(self->notification_callback);
    self->notification_callback = NULL;
    Py_XDECREF(self->notification_callback_param);
    self->notification_callback_param = NULL;
}


static PyObject *
my_mq_unlink(const char *name) {
    DPRINTF("unlinking mq name %s\n", name);
    if (-1 == mq_unlink(name)) {
        switch (errno) {
            case EACCES:
                PyErr_SetString(pPermissionsException,
                                "Permission denied");
            break;

            case ENOENT:
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "No queue exists with the specified name");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError, "The name is too long");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static int
mq_get_attrs(mqd_t mqd, struct mq_attr *attr) {
    attr->mq_flags = 0;
    attr->mq_maxmsg = 0;
    attr->mq_msgsize = 0;
    attr->mq_curmsgs = 0;

    if (-1 == mq_getattr(mqd, attr)) {
        switch (errno) {
            case EBADF:
            case EINVAL:
                PyErr_SetString(pExistentialException,
                                "The queue does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    return 0;

    error_return:
    return -1;
}


static PyObject *
MessageQueue_new(PyTypeObject *type, PyObject *args, PyObject *kwlist) {
    MessageQueue *self;

    self = (MessageQueue *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


static int
MessageQueue_init(MessageQueue *self, PyObject *args, PyObject *keywords) {
    NoneableName name;
    char temp_name[MAX_SAFE_NAME_LENGTH + 1];
    unsigned int flags = 0;
    long max_messages = QUEUE_MESSAGES_MAX_DEFAULT;
    long max_message_size = QUEUE_MESSAGE_SIZE_MAX_DEFAULT;
    PyObject *py_read = NULL;
    PyObject *py_write = NULL;
    struct mq_attr attr;
    static char *keyword_list[ ] = {"name", "flags", "mode", "max_messages",
                                    "max_message_size", "read", "write", NULL};

    // First things first -- initialize the self struct.
    self->mqd = POSIX_IPC_MQ_NO_VALUE;
    self->name = NULL;
    self->mode = 0600;
    self->notification_callback = NULL;
    self->notification_callback_param = NULL;

    // MessageQueue(name, flags = 0, mode=0600,
    //              max_messages=QUEUE_MESSAGES_MAX_DEFAULT,
    //              max_message_size=QUEUE_MESSAGE_SIZE_MAX_DEFAULT,
    //              read = True, write = True)

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O&|IillOO", keyword_list,
                                    &convert_name_param, &name, &flags,
                                    &(self->mode), &max_messages,
                                    &max_message_size, &py_read, &py_write))
        goto error_return;

    if ( !(flags & O_CREAT) && (flags & O_EXCL) ) {
        PyErr_SetString(PyExc_ValueError,
                "O_EXCL must be combined with O_CREAT");
        goto error_return;
    }

    if (name.is_none && ((flags & O_EXCL) != O_EXCL)) {
        PyErr_SetString(PyExc_ValueError,
                "Name can only be None if O_EXCL is set");
        goto error_return;
    }

    // read & write flags default to True, so if the user passed True I
    // set the object pointers to their default values of NULL. So here
    // NULL means True and any other value means False. Sorry for being
    // backwards.
    if (py_read && PyObject_IsTrue(py_read)) py_read = NULL;

    if (py_write && PyObject_IsTrue(py_write)) py_write = NULL;

    if ((!py_read) && (!py_write)) {
        flags |= O_RDWR;
        self->send_permitted = 1;
        self->receive_permitted = 1;
    }

    if ((!py_read) && (py_write)) {
        flags |= O_RDONLY;
        self->send_permitted = 0;
        self->receive_permitted = 1;
    }

    if ((py_read) && (!py_write)) {
        flags |= O_WRONLY;
        self->send_permitted = 1;
        self->receive_permitted = 0;
    }

    if ((py_read) && (py_write)) {
        PyErr_SetString(PyExc_ValueError, "At least one of read or write must be True");
        goto error_return;
    }

    // Params look OK, let's try to open/create the queue
    if (flags & O_CREAT) {
        // Set up the attr struct which is only needed when creating.
        attr.mq_flags = (flags & O_NONBLOCK) ? O_NONBLOCK : 0;
        attr.mq_maxmsg = max_messages;
        attr.mq_msgsize = max_message_size;
        attr.mq_curmsgs = 0;
    }

    if (name.is_none) {
        // (name == None) ==> generate a name for the caller
        do {
            errno = 0;
            create_random_name(temp_name);

            DPRINTF("calling mq_open, name=%s, flags=0x%x, mode=0%o, maxmsg=%ld, msgsize=%ld\n",
                    temp_name, flags, (int)self->mode, attr.mq_maxmsg, attr.mq_msgsize);
            self->mqd = mq_open(temp_name, flags, (mode_t)self->mode, &attr);

        } while ( ((mqd_t)-1 == self->mqd) && (EEXIST == errno) );

        // PyMalloc memory and copy the randomly-generated name to it.
        self->name = (char *)PyMem_Malloc(strlen(temp_name) + 1);
        if (self->name)
            strcpy(self->name, temp_name);
        else {
            PyErr_SetString(PyExc_MemoryError, "Out of memory");
            goto error_return;
        }
    }
    else {
        // (name != None) ==> use name supplied by the caller. It was
        // already converted to C by convert_name_param().
        self->name = name.name;

        if (flags & O_CREAT) {
            DPRINTF("calling mq_open, name=%s, flags=0x%x, mode=0%o, maxmsg=%ld, msgsize=%ld\n",
                    self->name, flags, (int)self->mode, attr.mq_maxmsg, attr.mq_msgsize);
            self->mqd = mq_open(self->name, flags, (mode_t)self->mode, &attr);
        }
        else {
            DPRINTF("calling mq_open, name=%s, flags=0x%x\n", self->name, flags);
            self->mqd = mq_open(self->name, flags);
        }
    }

    DPRINTF("mqd = %ld\n", (long)self->mqd);

    if ((mqd_t)-1 == self->mqd) {
        switch (errno) {
            case EINVAL:
                PyErr_SetString(PyExc_ValueError, "Invalid parameter(s)");
            break;

            case ENOSPC:
                PyErr_SetString(PyExc_OSError,
                                "Insufficient space for a new queue");
            break;

            case EACCES:
                PyErr_SetString(pPermissionsException, "Permission denied");
            break;

            case EEXIST:
                PyErr_SetString(pExistentialException,
                        "A queue with the specified name already exists");
            break;

            case ENOENT:
                PyErr_SetString(pExistentialException,
                                "No queue exists with the specified name");
            break;

            case EMFILE:
                PyErr_SetString(PyExc_OSError,
                    "This process already has the maximum number of files open");
            break;

            case ENFILE:
                PyErr_SetString(PyExc_OSError,
                    "The system limit on the total number of open files has been reached");
            break;

            case ENAMETOOLONG:
                PyErr_SetString(PyExc_ValueError, "The name is too long");
            break;

            case ENOMEM:
                PyErr_SetString(PyExc_MemoryError, "Not enough memory");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    // self->mqd and self->name are already populated. Here's where I get
    // the other two values.
    if (0 == mq_get_attrs(self->mqd, &attr)) {
        self->max_messages = attr.mq_maxmsg;
        self->max_message_size = attr.mq_msgsize;
    }
    else {
        // Oy vey, something has gone very wrong. The call to mq_open()
        // succeeded but mq_getattr() failed?!?
        PyErr_Clear();
        PyErr_SetString(pBaseException, "Unable to initialize object");
        goto error_return;
    }

    // Last but not least, get a reference to the interpreter state. I only
    // need this if the caller requests queue notifications that occur in
    // a new thread, so much of the time this goes unused.
    // It's my understanding that there's only one interpreter state to go
    // around, so no matter which thread I get the interpreter state from,
    // it will be the same interpreter state.
    self->interpreter = PyThreadState_Get()->interp;

    return 0;

    error_return:
    return -1;
}


static void
MessageQueue_dealloc(MessageQueue *self) {
    DPRINTF("dealloc\n");
    PyMem_Free(self->name);
    self->name = NULL;

    Py_XDECREF(self->notification_callback);
    self->notification_callback = NULL;
    Py_XDECREF(self->notification_callback_param);
    self->notification_callback_param = NULL;

    Py_TYPE(self)->tp_free((PyObject*)self);
}


static PyObject *
MessageQueue_send(MessageQueue *self, PyObject *args, PyObject *keywords) {
    NoneableTimeout timeout;
    long priority = 0;
    int rc = 0;
    static char *keyword_list[ ] = {"message", "timeout", "priority", NULL};
#if PY_MAJOR_VERSION > 2
    static char args_format[] = "s*|O&l";
    Py_buffer msg;
#else
    static char args_format[] = "s#|O&l";
    typedef struct {
        char *buf;
        unsigned long len;
    } MyBuffer;
    MyBuffer msg;
#endif

    // Initialize this to the default of None.
    timeout.is_none = 1;

    /* In Python >= 2.5, the Python argument specifier 's#' expects a
       py_ssize_t for its second parameter (msg.len). A ulong is long
       enough to fit a py_ssize_t.
       It might be too big, though, on platforms where a ulong is larger than
       py_ssize_t. Therefore I *must* initialize it to 0 so that whatever
       Python doesn't write to is zeroed out.
    */
    msg.len = 0;

    if (!PyArg_ParseTupleAndKeywords(args, keywords, args_format, keyword_list,
#if PY_MAJOR_VERSION > 2
                                     &msg,
#else
                                     &(msg.buf), &(msg.len),
#endif
                                     convert_timeout, &timeout,
                                     &priority))
        goto error_return;

    if (!self->send_permitted) {
        PyErr_SetString(pPermissionsException, "The queue is not open for writing");
        goto error_return;
    }

    if (msg.len > self->max_message_size) {
        PyErr_Format(PyExc_ValueError,
                     "The message must be no longer than %ld bytes",
                     self->max_message_size);
    }

    if ((priority < 0) || (priority > QUEUE_PRIORITY_MAX)) {
        PyErr_Format(PyExc_ValueError,
                     "The priority must be a positive number no greater than QUEUE_PRIORITY_MAX (%u)",
                     QUEUE_PRIORITY_MAX);
        goto error_return;
    }

    Py_BEGIN_ALLOW_THREADS
    // timeout == None: no timeout, i.e. wait forever.
    // timeout >= 0: wait no longer than t seconds before raising an error.
    if (timeout.is_none) {
        DPRINTF("calling mq_send(), mqd=%ld, msg len=%ld, priority=%ld\n",
                (long)self->mqd, (long)msg.len, priority);
        rc = mq_send(self->mqd, msg.buf, msg.len, (unsigned int)priority);
    }
    else {
        // Timeout is not None (i.e. is numeric)
        DPRINTF("calling mq_timedsend(), mqd=%ld, msg len=%ld, priority=%ld\n",
                (long)self->mqd, (long)msg.len, priority);
        DPRINTF("timeout tv_sec = %ld; timeout tv_nsec = %ld\n",
                timeout.timestamp.tv_sec, timeout.timestamp.tv_nsec);

        rc = mq_timedsend(self->mqd, msg.buf, msg.len, (unsigned int)priority,
                          &(timeout.timestamp));
    }
    Py_END_ALLOW_THREADS

    if (-1 == rc) {
        switch (errno) {
            case EBADF:
            case EINVAL:
                // The POSIX spec & Linux doc say that EINVAL can mean --
                // 1) self->mqd is not valid for writing
                // 2) timeout is < 0 or > one billion.
                // Since my code above guards against out-of-range
                // params, I expect only the first condition.
                PyErr_SetString(pExistentialException,
                    "The message queue does not exist or is not open for writing");
            break;

            case EINTR:
                /* If the signal was generated by Ctrl-C, calling
                PyErr_CheckSignals() here has the side effect of setting
                Python's error indicator. Otherwise there's a good chance
                it won't be set.
                http://groups.google.com/group/comp.lang.python/browse_thread/thread/ada39e984dfc3da6/fd6becbdce91a6be?#fd6becbdce91a6be
                */
                PyErr_CheckSignals();

                if (!(PyErr_Occurred() &&
                      PyErr_ExceptionMatches(PyExc_KeyboardInterrupt))
                   ) {
                    PyErr_Clear();
                    PyErr_SetString(pSignalException,
                                    "The wait was interrupted by a signal");
                }
                // else
                    // If KeyboardInterrupt error is set, I propogate that
                    // up to the caller.
            break;

            case EAGAIN:
            case ETIMEDOUT:
                PyErr_SetString(pBusyException, "The queue is full");
            break;

            case EMSGSIZE:
                // This should never happen since I checked message length
                // above, but who knows...
                PyErr_SetString(PyExc_ValueError, "The message is too long");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

#if PY_MAJOR_VERSION > 2
    PyBuffer_Release(&msg);
#endif

    Py_RETURN_NONE;

    error_return:
#if PY_MAJOR_VERSION > 2
    PyBuffer_Release(&msg);
#endif
    return NULL;
}


static PyObject *
MessageQueue_receive(MessageQueue *self, PyObject *args, PyObject *keywords) {
    NoneableTimeout timeout;
    char *msg = NULL;
    unsigned int priority = 0;
    ssize_t size = 0;
    PyObject *py_return_tuple = NULL;
    static char *keyword_list[ ] = {"timeout", NULL};

    // Initialize this to the default of None.
    timeout.is_none = 1;

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "|O&", keyword_list,
                                     convert_timeout, &timeout))
        goto error_return;

    if (!self->receive_permitted) {
        PyErr_SetString(pPermissionsException, "The queue is not open for reading");
        goto error_return;
    }

    msg = (char *)malloc(self->max_message_size);

    if (!msg) {
        PyErr_SetString(PyExc_MemoryError, "Out of memory");
        goto error_return;
    }

    Py_BEGIN_ALLOW_THREADS
    // timeout == None: no timeout, i.e. wait forever.
    // timeout >= 0: wait no longer than t seconds before raising an error.
    if (timeout.is_none) {
        DPRINTF("Calling mq_receive(), mqd=%ld; msg buffer length = %ld\n",
                (long)self->mqd, self->max_message_size);
        size = mq_receive(self->mqd, msg, self->max_message_size, &priority);
    }
    else {
        // Timeout is not None (i.e. is numeric)
        DPRINTF("Calling mq_timedreceive(), mqd=%ld; msg buffer length = %ld\n",
                (long)self->mqd, self->max_message_size);
        DPRINTF("timeout tv_sec = %ld; timeout tv_nsec = %ld\n",
                timeout.timestamp.tv_sec,
                timeout.timestamp.tv_nsec);

        size = mq_timedreceive(self->mqd, msg, self->max_message_size,
                               &priority, &(timeout.timestamp));
    }
    Py_END_ALLOW_THREADS

    if (-1 == size) {
        switch (errno) {
            case EBADF:
            case EINVAL:
                // The POSIX spec & Linux doc say that EINVAL has three
                // meanings --
                // 1) self->mqd is not open for reading
                // 2) timeout is < 0 or > one billion.
                // 3) msg len is out of range.
                // Since my code above guards against out-of-range
                // params, I expect only the first condition.
                PyErr_SetString(pExistentialException,
                                "The message queue does not exist or is not open for reading");
            break;

            case EINTR:
                /* If the signal was generated by Ctrl-C, calling
                PyErr_CheckSignals() here has the side effect of setting
                Python's error indicator. Otherwise there's a good chance
                it won't be set.
                http://groups.google.com/group/comp.lang.python/browse_thread/thread/ada39e984dfc3da6/fd6becbdce91a6be?#fd6becbdce91a6be
                */
                PyErr_CheckSignals();

                if (!(PyErr_Occurred() &&
                      PyErr_ExceptionMatches(PyExc_KeyboardInterrupt))
                   ) {
                    PyErr_Clear();
                    PyErr_SetString(pSignalException,
                                    "The wait was interrupted by a signal");
                }
                // else
                    // If KeyboardInterrupt error is set, I propogate that
                    // up to the caller.
            break;

            case EAGAIN:
            case ETIMEDOUT:
                PyErr_SetString(pBusyException, "The queue is empty");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    py_return_tuple = Py_BuildValue("NN",
#if PY_MAJOR_VERSION > 2
                                    PyBytes_FromStringAndSize(msg, size),
                                    PyLong_FromLong((long)priority)
#else
                                    PyString_FromStringAndSize(msg, size),
                                    PyInt_FromLong((long)priority)
#endif
                                   );

    free(msg);

    return py_return_tuple;

    error_return:
    free(msg);

    return NULL;
}


static PyObject *
MessageQueue_unlink(MessageQueue *self) {
    return my_mq_unlink(self->name);
}


void dprint_current_thread_id(void) {
    // Debug print only. Note that calling PyThreadState_Get() when there's
    // no current thread is a fatal error, so calling this can crash your
    // app.
    DPRINTF("Current thread has id %lx\n", PyThreadState_Get()->thread_id);
}


void process_notification(union sigval notification_data) {
    /* Invoked by the system in a new thread as notification of a message
       arriving in the queue. */
    PyObject *py_args;
    PyObject *py_result;
    MessageQueue *self = notification_data.sival_ptr;
    PyObject *callback_function = NULL;
    PyObject *callback_param = NULL;
    PyGILState_STATE gstate;

    DPRINTF("C thread %lx invoked, calling PyGILState_Ensure()\n", (unsigned long)pthread_self());

    gstate = PyGILState_Ensure();

    /* Notifications are one-offs; the caller must re-register if he wants
       more. Therefore I must discard my pointers to the callback function
       and param after the callback is complete.

       But the caller may want to re-request notification during the callback.
       If he does so, MessageQueue_request_notification() will be invoked
       and self->notification_callback and ->notification_callback_param
       will get overwritten. Therefore I need to make copies of them here
       under the assumption that my self-> pointers won't survive the
       callback and DECREF them after the callback is complete.
    */
    callback_function = self->notification_callback;
    callback_param = self->notification_callback_param;
    self->notification_callback = NULL;
    self->notification_callback_param = NULL;

    // Perform the callback.
    DPRINTF("Performing the callback...\n");
    py_args = Py_BuildValue("(O)", callback_param);
    py_result = PyObject_CallObject(callback_function, py_args);
    Py_DECREF(py_args);

    // If py_result is NULL, the call failed. However, I want to return
    // control to the main thread before I raise an error, so I deal with
    // py_result later.

    DPRINTF("Done calling\n");

    // Now I can clean these up safely.
    Py_XDECREF(callback_function);
    Py_XDECREF(callback_param);

    if (!py_result) {
        DPRINTF("Invoking the callback failed\n");
        // FIXME - setting the error indicator here doesn't seem to
        // propogate up to the main thread, so I can't figure out how to
        // squawk if the callback fails.
        //PyErr_SetString(pBaseException, "Invoking the callback failed");
    }

    Py_XDECREF(py_result);

    /* Release the thread. No Python API allowed beyond this point. */
    DPRINTF("Calling PyGILState_Release()\n");
    PyGILState_Release(gstate);

    DPRINTF("exiting thread\n");
};

static PyObject *
MessageQueue_request_notification(MessageQueue *self, PyObject *args,
                                  PyObject *keywords) {
    struct sigevent notification;
    PyObject *py_callback = NULL;
    PyObject *py_callback_param = NULL;
    PyObject *py_notification = Py_None;
    int param_is_ok = 1;
    static char *keyword_list[ ] = {"notification", NULL};

    // request_notification(notification = None)

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "|O", keyword_list,
                                     &py_notification))
        goto error_return;

    // py_notification can be None ==> cancel, an int ==> signal,
    // or a tuple of (callback function, param)
    if (py_notification == Py_None) {
        notification.sigev_notify = SIGEV_NONE;
    }
#if PY_MAJOR_VERSION > 2
    else if (PyLong_Check(py_notification))
#else
    else if (PyInt_Check(py_notification))
#endif
    {
        notification.sigev_notify = SIGEV_SIGNAL;
#if PY_MAJOR_VERSION > 2
        notification.sigev_signo = (int)PyLong_AsLong(py_notification);
#else
        notification.sigev_signo = (int)PyInt_AsLong(py_notification);
#endif
    }
    else if (PyTuple_Check(py_notification)) {
        notification.sigev_notify = SIGEV_THREAD;

        if (2 == PyTuple_Size(py_notification)) {
            py_callback = PyTuple_GetItem(py_notification, 0);
            py_callback_param = PyTuple_GetItem(py_notification, 1);

            if (!PyCallable_Check(py_callback))
                param_is_ok = 0;
        }
        else
            param_is_ok = 0;
    }
    else
        param_is_ok = 0;

    if (!param_is_ok) {
        PyErr_SetString(PyExc_ValueError,
                        "The notification must be None, an integer, or a tuple of (function, parameter)");
        goto error_return;
    }

    // At this point the param is either None, in which case I want to
    // cancel any existing notification request, or it is requesting
    // signal or thread notification, in which case I also want to cancel
    // any existing notification request.
    mq_cancel_notification(self);

    if (SIGEV_THREAD == notification.sigev_notify) {
        // I have to do a bit more work before calling mq_notify().

        // Store the new callback & param in self
        Py_INCREF(py_callback);
        Py_INCREF(py_callback_param);
        self->notification_callback = py_callback;
        self->notification_callback_param = py_callback_param;

        // Set up notification struct for passing to mq_notify()
        notification.sigev_value.sival_ptr = self;
        notification.sigev_notify_function = process_notification;
        notification.sigev_notify_attributes = NULL;

        // When notification occurs, it will be in a (new) C thread. In that
        // thread I'll create a Python thread but beforehand, threads must be
        // initialized. This is only necessary for Python 2.x and ≤ 3.6.
        // In Python 3.7, initializing threads (and the GIL) became the job of
        // Py_Initialize(), so it doesn't need to be done explicitly here.
#if PY_MAJOR_VERSION < 3 || PY_MINOR_VERSION < 7
        if (!PyEval_ThreadsInitialized()) {
            DPRINTF("calling PyEval_InitThreads()\n");
            PyEval_InitThreads();
        }
#endif

        dprint_current_thread_id();
    }

    if (SIGEV_NONE != notification.sigev_notify) {
        // request notification
        if (-1 == mq_notify(self->mqd, &notification)) {
            switch (errno) {
                case EBUSY:
                    PyErr_SetString(pBusyException,
                        "The queue is already delivering notifications elsewhere");
                break;

                default:
                    PyErr_SetFromErrno(PyExc_OSError);
                break;
            }

            // If setting up the notification failed, there's no reason to
            // hang on to these references.
            Py_XDECREF(self->notification_callback);
            self->notification_callback = NULL;
            Py_XDECREF(self->notification_callback_param);
            self->notification_callback_param = NULL;

            goto error_return;
        }
    }

    DPRINTF("exiting MessageQueue_request_notification()\n");

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


static PyObject *
MessageQueue_close(MessageQueue *self) {
    if (-1 == mq_close(self->mqd)) {
        switch (errno) {
            case EINVAL:
            case EBADF:
                PyErr_SetString(pExistentialException,
                                "The queue does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }
        goto error_return;
    }
    else {
        // Close was successful so the handle is no longer valid.
        self->mqd = POSIX_IPC_MQ_NO_VALUE;
    }

    Py_RETURN_NONE;

    error_return:
    return NULL;
}


PyObject *
MessageQueue_get_mqd(MessageQueue *self) {
    // This is a little awkward because an mqd is a void * under Solaris
    // and an int under Linux. I cast it and hope for the best.    :-/
#if PY_MAJOR_VERSION > 2
    return PyLong_FromLong((long)self->mqd);
#else
    if ( ((long)self->mqd > PY_INT_MAX) || ((long)self->mqd < (0 - PY_INT_MAX)) )
        return PyLong_FromLong((long)self->mqd);
    else
        return PyInt_FromLong((long)self->mqd);
#endif
}


PyObject *
MessageQueue_fileno(MessageQueue *self) {
	return MessageQueue_get_mqd(self);
}


PyObject *
MessageQueue_get_block(MessageQueue *self) {
    struct mq_attr attr;

    if (-1 == mq_get_attrs(self->mqd, &attr))
        return NULL;
    else {
        if (attr.mq_flags & O_NONBLOCK)
            Py_RETURN_FALSE;
        else
            Py_RETURN_TRUE;
    }
}


static int
MessageQueue_set_block(MessageQueue *self, PyObject *value) {
    struct mq_attr attr;

    attr.mq_flags = PyObject_IsTrue(value) ? 0 : O_NONBLOCK;

    if (-1 == mq_setattr(self->mqd, &attr, NULL)) {
        switch (errno) {
            case EBADF:
                PyErr_SetString(pExistentialException,
                                "The queue does not exist");
            break;

            default:
                PyErr_SetFromErrno(PyExc_OSError);
            break;
        }

        goto error_return;
    }

    return 0;

    error_return:
    return -1;
}

PyObject *
MessageQueue_get_current_messages(MessageQueue *self) {
    struct mq_attr attr;

    if (-1 == mq_get_attrs(self->mqd, &attr))
        return NULL;
    else
        return Py_BuildValue("k", (unsigned long)attr.mq_curmsgs);
}

// end of #ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
#endif


/*   =====  End Message Queue implementation functions ===== */




/*
 *
 * Semaphore meta stuff for describing myself to Python
 *
 */

static PyMemberDef Semaphore_members[] = {
    {   "name",
        T_STRING,
        offsetof(Semaphore, name),
        READONLY,
        "The name specified in the constructor"
    },
    {   "mode",
        T_LONG,
        offsetof(Semaphore, mode),
        READONLY,
        "The mode specified in the constructor"
    },
    {NULL} /* Sentinel */
};


static PyMethodDef Semaphore_methods[] = {
    {   "__enter__",
        (PyCFunction)Semaphore_enter,
        METH_NOARGS,
    },
    {   "__exit__",
        (PyCFunction)Semaphore_exit,
        METH_VARARGS,
    },
    {   "acquire",
        (PyCFunction)Semaphore_acquire,
        METH_VARARGS | METH_KEYWORDS,
        "Acquire (grab) the semaphore, waiting if necessary"
    },
    {   "release",
        (PyCFunction)Semaphore_release,
        METH_NOARGS,
        "Release the semaphore"
    },
    {   "close",
        (PyCFunction)Semaphore_close,
        METH_NOARGS,
        "Close the semaphore for this process."
    },
    {   "unlink",
        (PyCFunction)Semaphore_unlink,
        METH_NOARGS,
        "Unlink (remove) the semaphore."
    },
    {NULL, NULL, 0, NULL} /* Sentinel */
};


static PyGetSetDef Semaphore_getseters[] = {
#ifdef SEM_GETVALUE_EXISTS
    {"value", (getter)Semaphore_getvalue, (setter)NULL, "value", NULL},
#endif
    {NULL} /* Sentinel */
};


static PyTypeObject SemaphoreType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "posix_ipc.Semaphore",              // tp_name
    sizeof(Semaphore),                  // tp_basicsize
    0,                                  // tp_itemsize
    (destructor) Semaphore_dealloc,     // tp_dealloc
    0,                                  // tp_print
    0,                                  // tp_getattr
    0,                                  // tp_setattr
    0,                                  // tp_compare
    (reprfunc) sem_repr,                // tp_repr
    0,                                  // tp_as_number
    0,                                  // tp_as_sequence
    0,                                  // tp_as_mapping
    0,                                  // tp_hash
    0,                                  // tp_call
    (reprfunc) sem_str,                 // tp_str
    0,                                  // tp_getattro
    0,                                  // tp_setattro
    0,                                  // tp_as_buffer
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
                                        // tp_flags
    "POSIX semaphore object",           // tp_doc
    0,                                  // tp_traverse
    0,                                  // tp_clear
    0,                                  // tp_richcompare
    0,                                  // tp_weaklistoffset
    0,                                  // tp_iter
    0,                                  // tp_iternext
    Semaphore_methods,                  // tp_methods
    Semaphore_members,                  // tp_members
    Semaphore_getseters,                // tp_getset
    0,                                  // tp_base
    0,                                  // tp_dict
    0,                                  // tp_descr_get
    0,                                  // tp_descr_set
    0,                                  // tp_dictoffset
    (initproc) Semaphore_init,          // tp_init
    0,                                  // tp_alloc
    (newfunc) Semaphore_new,            // tp_new
    0,                                  // tp_free
    0,                                  // tp_is_gc
    0                                   // tp_bases
};


/*
 *
 * Shared memory meta stuff for describing myself to Python
 *
 */


static PyMemberDef SharedMemory_members[] = {
    {   "name",
        T_STRING,
        offsetof(SharedMemory, name),
        READONLY,
        "The name specified in the constructor"
    },
    {   "fd",
        T_INT,
        offsetof(SharedMemory, fd),
        READONLY,
        "Shared memory segment file descriptor"
    },
    {   "mode",
        T_LONG,
        offsetof(SharedMemory, mode),
        READONLY,
        "The mode specified in the constructor"
    },
    {NULL} /* Sentinel */
};


static PyMethodDef SharedMemory_methods[] = {
    {   "close_fd",
        (PyCFunction)SharedMemory_close_fd,
        METH_NOARGS,
        "Closes the file descriptor associated with the shared memory."
    },
    {   "fileno",
        (PyCFunction)SharedMemory_fileno,
        METH_NOARGS,
        "Returns the shared memory's file descriptor (same as the fd property)."
    },
    {   "unlink",
        (PyCFunction)SharedMemory_unlink,
        METH_NOARGS,
        "Unlink (remove) the shared memory."
    },
    {NULL, NULL, 0, NULL} /* Sentinel */
};


static PyGetSetDef SharedMemory_getseters[] = {
    // size is read-only
    {   "size",
        (getter)SharedMemory_getsize,
        (setter)NULL,
        "size",
        NULL
    },
    {NULL} /* Sentinel */
};


static PyTypeObject SharedMemoryType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "posix_ipc.SharedMemory",           // tp_name
    sizeof(SharedMemory),               // tp_basicsize
    0,                                  // tp_itemsize
    (destructor) SharedMemory_dealloc,  // tp_dealloc
    0,                                  // tp_print
    0,                                  // tp_getattr
    0,                                  // tp_setattr
    0,                                  // tp_compare
    (reprfunc) shm_repr,                // tp_repr
    0,                                  // tp_as_number
    0,                                  // tp_as_sequence
    0,                                  // tp_as_mapping
    0,                                  // tp_hash
    0,                                  // tp_call
    (reprfunc) shm_str,                 // tp_str
    0,                                  // tp_getattro
    0,                                  // tp_setattro
    0,                                  // tp_as_buffer
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
                                        // tp_flags
    "POSIX shared memory object",       // tp_doc
    0,                                  // tp_traverse
    0,                                  // tp_clear
    0,                                  // tp_richcompare
    0,                                  // tp_weaklistoffset
    0,                                  // tp_iter
    0,                                  // tp_iternext
    SharedMemory_methods,               // tp_methods
    SharedMemory_members,               // tp_members
    SharedMemory_getseters,             // tp_getset
    0,                                  // tp_base
    0,                                  // tp_dict
    0,                                  // tp_descr_get
    0,                                  // tp_descr_set
    0,                                  // tp_dictoffset
    (initproc) SharedMemory_init,       // tp_init
    0,                                  // tp_alloc
    (newfunc) SharedMemory_new,         // tp_new
    0,                                  // tp_free
    0,                                  // tp_is_gc
    0                                   // tp_bases
};


/*
 *
 * Message queue meta stuff for describing myself to Python
 *
 */

#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS

static PyMemberDef MessageQueue_members[] = {
    {   "name",
        T_STRING,
        offsetof(MessageQueue, name),
        READONLY,
        "The name specified in the constructor"
    },
    {   "max_messages",
        T_LONG,
        offsetof(MessageQueue, max_messages),
        READONLY,
        "Queue slots"
    },
    {   "max_message_size",
        T_LONG,
        offsetof(MessageQueue, max_message_size),
        READONLY,
        "Maximum number of bytes per message"
    },
    {   "mode",
        T_LONG,
        offsetof(MessageQueue, mode),
        READONLY,
        "The mode specified in the constructor"
    },
    {NULL} /* Sentinel */
};


static PyMethodDef MessageQueue_methods[] = {
    {   "send",
        (PyCFunction)MessageQueue_send,
        METH_VARARGS | METH_KEYWORDS,
        "Send a message via the queue"
    },
    {   "receive",
        (PyCFunction)MessageQueue_receive,
        METH_VARARGS | METH_KEYWORDS,
        "Receive a message from the queue"
    },
    {   "close",
        (PyCFunction)MessageQueue_close,
        METH_NOARGS,
        "Close the queue's descriptor"
    },
    {   "unlink",
        (PyCFunction)MessageQueue_unlink,
        METH_NOARGS,
        "Unlink the queue"
    },
    {   "request_notification",
        (PyCFunction)MessageQueue_request_notification,
        METH_VARARGS | METH_KEYWORDS,
        "Request notification of the queue becoming non-empty"
    },
    {   "fileno",
        (PyCFunction)MessageQueue_fileno,
        METH_NOARGS,
        "Returns the queue's descriptor (same as the mqd property)."
    },

    {NULL, NULL, 0, NULL} /* Sentinel */
};


static PyGetSetDef MessageQueue_getseters[] = {
    {   "block",
        (getter)MessageQueue_get_block,
        (setter)MessageQueue_set_block,
        "block",
        NULL
    },
    {   "mqd",
        (getter)MessageQueue_get_mqd,
        (setter)NULL,
        "Message queue descriptor",
        NULL
    },
    {   "current_messages",
        (getter)MessageQueue_get_current_messages,
        (setter)NULL,
        "current_message_count",
        NULL
    },
    {NULL} /* Sentinel */
};

static PyTypeObject MessageQueueType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "posix_ipc.MessageQueue",           // tp_name
    sizeof(MessageQueue),               // tp_basicsize
    0,                                  // tp_itemsize
    (destructor) MessageQueue_dealloc,  // tp_dealloc
    0,                                  // tp_print
    0,                                  // tp_getattr
    0,                                  // tp_setattr
    0,                                  // tp_compare
    (reprfunc) mq_repr,                 // tp_repr
    0,                                  // tp_as_number
    0,                                  // tp_as_sequence
    0,                                  // tp_as_mapping
    0,                                  // tp_hash
    0,                                  // tp_call
    (reprfunc) mq_str,                  // tp_str
    0,                                  // tp_getattro
    0,                                  // tp_setattro
    0,                                  // tp_as_buffer
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
                                        // tp_flags
    "POSIX message queue object",       // tp_doc
    0,                                  // tp_traverse
    0,                                  // tp_clear
    0,                                  // tp_richcompare
    0,                                  // tp_weaklistoffset
    0,                                  // tp_iter
    0,                                  // tp_iternext
    MessageQueue_methods,               // tp_methods
    MessageQueue_members,               // tp_members
    MessageQueue_getseters,             // tp_getset
    0,                                  // tp_base
    0,                                  // tp_dict
    0,                                  // tp_descr_get
    0,                                  // tp_descr_set
    0,                                  // tp_dictoffset
    (initproc) MessageQueue_init,       // tp_init
    0,                                  // tp_alloc
    (newfunc) MessageQueue_new,         // tp_new
    0,                                  // tp_free
    0,                                  // tp_is_gc
    0                                   // tp_bases
};

// end of #ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
#endif


/*
 *
 * Module-level functions & meta stuff
 *
 */

static PyObject *
posix_ipc_unlink_semaphore(PyObject *self, PyObject *args) {
    const char *name;

    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;
    else
        return my_sem_unlink(name);
}


static PyObject *
posix_ipc_unlink_shared_memory(PyObject *self, PyObject *args) {
    const char *name;

    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;
    else
        return my_shm_unlink(name);
}


#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
static PyObject *
posix_ipc_unlink_message_queue(PyObject *self, PyObject *args) {
    const char *name;

    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;
    else
        return my_mq_unlink(name);
}
#endif


static PyMethodDef module_methods[ ] = {
    {   "unlink_semaphore",
        (PyCFunction)posix_ipc_unlink_semaphore,
        METH_VARARGS,
        "Unlink a semaphore"
    },
    {   "unlink_shared_memory",
        (PyCFunction)posix_ipc_unlink_shared_memory,
        METH_VARARGS,
        "Unlink shared memory"
    },
#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
    {   "unlink_message_queue",
        (PyCFunction)posix_ipc_unlink_message_queue,
        METH_VARARGS,
        "Unlink a message queue"
    },
#endif
    {NULL} /* Sentinel */
};


#if PY_MAJOR_VERSION > 2
static struct PyModuleDef this_module = {
    PyModuleDef_HEAD_INIT,  // m_base
    "posix_ipc",            // m_name
    "POSIX IPC module",     // m_doc
    -1,                     // m_size (space allocated for module globals)
    module_methods,         // m_methods
    NULL,                   // m_reload
    NULL,                   // m_traverse
    NULL,                   // m_clear
    NULL                    // m_free
};
#endif

/* Module init function */
#if PY_MAJOR_VERSION > 2
#define POSIX_IPC_INIT_FUNCTION_NAME PyInit_posix_ipc
#else
#define POSIX_IPC_INIT_FUNCTION_NAME initposix_ipc
#endif

/* Module init function */
PyMODINIT_FUNC
POSIX_IPC_INIT_FUNCTION_NAME(void) {
    PyObject *module;
    PyObject *module_dict;

    // I call this in case I'm asked to create any random names.
    srand((unsigned int)time(NULL));

#if PY_MAJOR_VERSION > 2
    module = PyModule_Create(&this_module);
#else
    module = Py_InitModule3("posix_ipc", module_methods, "POSIX IPC module");
#endif

    if (!module)
        goto error_return;

    if (PyType_Ready(&SemaphoreType) < 0)
        goto error_return;

    if (PyType_Ready(&SharedMemoryType) < 0)
        goto error_return;

#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
    if (PyType_Ready(&MessageQueueType) < 0)
        goto error_return;
#endif

    Py_INCREF(&SemaphoreType);
    PyModule_AddObject(module, "Semaphore", (PyObject *)&SemaphoreType);

    Py_INCREF(&SharedMemoryType);
    PyModule_AddObject(module, "SharedMemory", (PyObject *)&SharedMemoryType);

#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
    Py_INCREF(&MessageQueueType);
    PyModule_AddObject(module, "MessageQueue", (PyObject *)&MessageQueueType);
#endif


    PyModule_AddStringConstant(module, "VERSION", POSIX_IPC_VERSION);
    PyModule_AddStringConstant(module, "__version__", POSIX_IPC_VERSION);
    PyModule_AddStringConstant(module, "__copyright__", "Copyright 2018 Philip Semanchuk");
    PyModule_AddStringConstant(module, "__author__", "Philip Semanchuk");
    PyModule_AddStringConstant(module, "__license__", "BSD");

    PyModule_AddIntConstant(module, "O_CREAT", O_CREAT);
    PyModule_AddIntConstant(module, "O_EXCL", O_EXCL);
    PyModule_AddIntConstant(module, "O_CREX", O_CREAT | O_EXCL);
    PyModule_AddIntConstant(module, "O_TRUNC", O_TRUNC);
#ifdef MESSAGE_QUEUE_SUPPORT_EXISTS
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "MESSAGE_QUEUES_SUPPORTED", Py_True);
    PyModule_AddIntConstant(module, "O_RDONLY", O_RDONLY);
    PyModule_AddIntConstant(module, "O_WRONLY", O_WRONLY);
    PyModule_AddIntConstant(module, "O_RDWR", O_RDWR);
    PyModule_AddIntConstant(module, "O_NONBLOCK", O_NONBLOCK);
    PyModule_AddIntConstant(module, "QUEUE_MESSAGES_MAX_DEFAULT", QUEUE_MESSAGES_MAX_DEFAULT);
    PyModule_AddIntConstant(module, "QUEUE_MESSAGE_SIZE_MAX_DEFAULT", QUEUE_MESSAGE_SIZE_MAX_DEFAULT);
    PyModule_AddIntConstant(module, "QUEUE_PRIORITY_MAX", QUEUE_PRIORITY_MAX);
#ifdef SIGRTMAX
    // SIGRTMIN and SIGRTMAX are only defined on platforms that support
    // the Realtime Signals Extension (RTS). NetBSD prior to 6.0 is an
    // example of a platform that doesn't support RTS.
    PyModule_AddIntConstant(module, "USER_SIGNAL_MIN", SIGRTMIN);
    PyModule_AddIntConstant(module, "USER_SIGNAL_MAX", SIGRTMAX);
#endif
#else
    Py_INCREF(Py_False);
    PyModule_AddObject(module, "MESSAGE_QUEUES_SUPPORTED", Py_False);
#endif

    PyModule_AddIntConstant(module, "PAGE_SIZE", PAGE_SIZE);

    PyModule_AddIntConstant(module, "SEMAPHORE_VALUE_MAX", SEM_VALUE_MAX);

#ifdef SEM_TIMEDWAIT_EXISTS
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "SEMAPHORE_TIMEOUT_SUPPORTED", Py_True);
#else
    Py_INCREF(Py_False);
    PyModule_AddObject(module, "SEMAPHORE_TIMEOUT_SUPPORTED", Py_False);
#endif

#ifdef SEM_GETVALUE_EXISTS
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "SEMAPHORE_VALUE_SUPPORTED", Py_True);
#else
    Py_INCREF(Py_False);
    PyModule_AddObject(module, "SEMAPHORE_VALUE_SUPPORTED", Py_False);
#endif

    if (!(module_dict = PyModule_GetDict(module)))
        goto error_return;

    // Exceptions
    if (!(pBaseException = PyErr_NewException("posix_ipc.Error", NULL, NULL)))
        goto error_return;
    else
        PyDict_SetItemString(module_dict, "Error", pBaseException);

    if (!(pSignalException = PyErr_NewException("posix_ipc.SignalError", pBaseException, NULL)))
        goto error_return;
    else
        PyDict_SetItemString(module_dict, "SignalError", pSignalException);

    if (!(pPermissionsException = PyErr_NewException("posix_ipc.PermissionsError", pBaseException, NULL)))
        goto error_return;
    else
        PyDict_SetItemString(module_dict, "PermissionsError", pPermissionsException);

    if (!(pExistentialException = PyErr_NewException("posix_ipc.ExistentialError", pBaseException, NULL)))
        goto error_return;
    else
        PyDict_SetItemString(module_dict, "ExistentialError", pExistentialException);

    if (!(pBusyException = PyErr_NewException("posix_ipc.BusyError", pBaseException, NULL)))
        goto error_return;
    else
        PyDict_SetItemString(module_dict, "BusyError", pBusyException);

#if PY_MAJOR_VERSION > 2
    return module;
#endif

    error_return:
#if PY_MAJOR_VERSION > 2
    return NULL;
#else
    ; // Nothing to do
#endif
}
