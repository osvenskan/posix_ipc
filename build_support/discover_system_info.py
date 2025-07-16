import subprocess
import platform
import os
import sys

# Set these to None for compile/link debugging or subprocess.PIPE to silence
# compiler warnings and errors.
STDOUT = subprocess.PIPE
STDERR = subprocess.PIPE
# STDOUT = None
# STDERR = None


class DiscoveryError(Exception):
    '''Exception raised when this script is unable to discover a value that it needs.'''
    pass


class POSIXNonComplianceWarning(UserWarning):
    '''Warning emitted when the underlying OS appears not to be POSIX compliant. POSIX compliance
    ensures (among other things) that important system information is available via sysconf().
    See https://github.com/osvenskan/posix_ipc/issues/81 for details.
    '''
    pass


def does_build_succeed(filename, linker_options=""):
    # Utility function that returns True if the file compiles and links
    # successfully, False otherwise.
    # Two things to note here --
    #   - If there's a linker option like -lrt, it needs to come *after*
    #     the specification of the C file or linking will fail on Ubuntu 11.10
    #     (maybe because of the gcc version?)
    #   - Some versions of Linux place the sem_xxx() functions in libpthread.
    #     Rather than testing whether or not it's needed, I just specify it
    #     everywhere since it's harmless to specify it when it's not needed.
    cc = os.getenv("CC", "cc")
    cmd = "%s -Wall -o ./build_support/src/foo ./build_support/src/%s %s -lpthread" % (cc, filename, linker_options)

    p = subprocess.Popen(cmd, shell=True, stdout=STDOUT, stderr=STDERR)

    # p.wait() returns the process' return code, so 0 implies that
    # the compile & link succeeded.
    return not bool(p.wait())


def compile_and_run(filename, linker_options=""):
    # Utility function that returns the stdout output from running the
    # compiled source file; None if the compile fails.
    cc = os.getenv("CC", "cc")
    cmd = "%s -Wall -o ./build_support/src/foo %s ./build_support/src/%s" % (cc, linker_options, filename)

    p = subprocess.Popen(cmd, shell=True, stdout=STDOUT, stderr=STDERR)

    if p.wait():
        # uh-oh, compile failed
        return None
    
    try:
        s = subprocess.Popen(["./build_support/src/foo"],
                             stdout=subprocess.PIPE).communicate()[0]
        return s.strip().decode()
    except Exception:
        # execution resulted in an error
        return None


def get_sysctl_value(name):
    """Given a sysctl name (e.g. 'kern.mqueue.maxmsg'), returns sysctl's value
    for that variable or None if the sysctl call fails (unknown name, not
    a BSD-ish system, etc.)

    Only makes sense on systems that implement sysctl (BSD derivatives).
    """
    s = None
    try:
        # I redirect stderr to /dev/null because if sysctl is availble but
        # doesn't know about the particular item I'm querying, it will
        # kvetch with a message like 'second level name mqueue in
        # kern.mqueue.maxmsg is invalid'. This always happens under OS X
        # (which doesn't have any kern.mqueue values) and under FreeBSD when
        # the mqueuefs kernel module isn't loaded.
        s = subprocess.Popen(["sysctl", "-n", name],
                             stdout=subprocess.PIPE,
                             stderr=open(os.devnull, 'rw')).communicate()[0]
        s = s.strip().decode()
    except:
        pass

    return s


def maybe_get_sysconf_value(name, complain_if_not_present=False):
    """Returns the value of a sysconf entry (e.g. 'SC_PAGESIZE') if the entry exists. If the value
    isn't available via sysconf, this function returns None.

    When complain_if_not_present is True, that means the sysconf value must be present for the
    system to be POSIX compliant. If the value is required but not present, this function raises
    a POSIXNonComplianceWarning to alert the user.

    Reference: https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/functions/sysconf.html
    """
    value = None

    # Years ago, Cygwin didn't support os.sysconf_names. That has probably changed, but I don't
    # want to assume.
    if hasattr(os, 'sysconf_names'):
        if name in os.sysconf_names:
            value = os.sysconf(name)

    if complain_if_not_present and (value is None):
        raise POSIXNonComplianceWarning(f'Value "{name}" is missing from sysconf')

    return value


def sniff_realtime_lib():
    rc = None
    filename = "sniff_realtime_lib.c"

    if does_build_succeed(filename):
        # Realtime libs not needed
        rc = False
    else:
        # cc failed when not linked to realtime libs; let's try again
        # with the realtime libs involved and see if things go better.
        if does_build_succeed(filename, "-lrt"):
            # Realtime libs are needed
            rc = True

    if rc is None:
        raise DiscoveryError('Unable to determine whether realtime lib is needed to build')

    return rc


def sniff_sem_getvalue(linker_options):
    return does_build_succeed("sniff_sem_getvalue.c", linker_options)


def sniff_sem_timedwait(linker_options):
    return does_build_succeed("sniff_sem_timedwait.c", linker_options)


def sniff_sem_value_max():
    # default is to return None which means that it is #defined in a standard
    # header file and doesn't need to be added to my custom header file.
    sem_value_max = None

    if not does_build_succeed("sniff_sem_value_max.c"):
        # OpenSolaris 2008.05 doesn't #define SEM_VALUE_MAX. (This may
        # be true elsewhere too.) Ask sysconf() instead if it exists.
        # Note that sys.sysconf_names doesn't exist under Cygwin.
        if hasattr(os, "sysconf_names") and \
           ("SC_SEM_VALUE_MAX" in os.sysconf_names):
            sem_value_max = os.sysconf("SC_SEM_VALUE_MAX")
        else:
            # This value of last resort should be #defined everywhere. What
            # could possibly go wrong?
            sem_value_max = "_POSIX_SEM_VALUE_MAX"

    return sem_value_max


def sniff_page_size():
    # 4096 is a common page size on x86. As the world moves increasingly to ARM architectures,
    # this might not be a good default anymore, but the default value isn't really supposed to
    # be used except when all else fails (and in that case the user gets a warning).
    DEFAULT_PAGE_SIZE = 4096

    page_size = None

    # When cross compiling under cibuildwheel, I need to rely on their custom env var to set the
    # page size correctly. See https://github.com/osvenskan/posix_ipc/issues/58
    if 'arm' in os.getenv('_PYTHON_HOST_PLATFORM', ''):
        page_size = 16384

    if not page_size:
        # Maybe I can find page size in os.sysconf(). If so, that saves a compilation step.
        if 'SC_PAGESIZE' in os.sysconf_names:
            page_size = os.sysconf('SC_PAGESIZE')

    if not page_size:
        # OK, I have to do it the hard way. I don't need to worry about linker options here
        # because I'm not calling any functions, just getting the value of a #define.
        page_size = compile_and_run("sniff_page_size.c")

    if not page_size:
        raise DiscoveryError('Unable to determine page size')

    return page_size


def sniff_mq_existence(linker_options):
    return does_build_succeed("sniff_mq_existence.c", linker_options)


def sniff_mq_prio_max():
    '''Returns the value of MQ_PRIO_MAX, formatted for inclusion in system_info.h.

    Raises a DiscoveryError exception if unable to determine the value.
    '''
    # Max queue priority should be present in sysconf() on POSIX-compliant systems, and checking
    # sysconf is easier than invoking the compiler.
    max_priority = maybe_get_sysconf_value('SC_MQ_PRIO_MAX', True)

    if not max_priority:
        # OK, try to get it via compilation.
        max_priority = compile_and_run("sniff_mq_prio_max.c")

    # Regardless of where I got the value from, it should be int-able (if it's not an int already).
    try:
        max_priority = int(max_priority)
    except Exception:
        # I don't care why the conversion to int failed.
        max_priority = None

    # At this point, max_priority is an int, or None.

    # Under OS X, os.sysconf("SC_MQ_PRIO_MAX") returns -1. This is still true in June 2025 under
    # MacOS 15.5. sniff_mq_prio_max() shouldn't even be called when building on the Mac, but
    # I'll leave this code here because maybe Mac isn't the only platform that behaves that way.
    if max_priority and (max_priority < 0):
        max_priority = None

    if max_priority is None:
        # At this point, I've exhausted all of my options.
        raise DiscoveryError('Unable to determine max message queue priority')

    # Adjust for the fact that these are 0-based values; i.e. permitted
    # priorities range from 0 - (MQ_PRIO_MAX - 1). So why not just make
    # the #define one smaller? Because this one goes up to eleven...
    max_priority -= 1

    # priority is an unsigned int
    return str(max_priority).strip() + "U"


def sniff_mq_max_messages():
    # This value is not defined by POSIX.

    # On most systems I've tested, msg Qs are implemented via mmap-ed files
    # or a similar interface, so the only theoretical limits are imposed by the
    # file system. In practice, Linux and *BSD impose some fairly tight
    # limits.

    # On Linux it's available in a /proc file and often defaults to the wimpy
    # value of 10.

    # On FreeBSD (and other BSDs, I assume), it's available via sysctl as
    # kern.mqueue.maxmsg. On my FreeBSD 9.1 test system, it defaults to 100.

    # mqueue.h defines mq_attr.mq_maxmsg as a C long, so that's
    # a practical limit for this value.

    # ref: http://linux.die.net/man/7/mq_overview
    # ref: http://www.freebsd.org/cgi/man.cgi?query=mqueuefs&sektion=5&manpath=FreeBSD+7.0-RELEASE
    # http://fxr.watson.org/fxr/source/kern/uipc_mqueue.c?v=FREEBSD91#L195
    # ref: http://groups.google.com/group/comp.unix.solaris/browse_thread/thread/aa223fc7c91f8c38
    # ref: http://cygwin.com/cgi-bin/cvsweb.cgi/src/winsup/cygwin/posix_ipc.cc?cvsroot=src
    # ref: http://cygwin.com/cgi-bin/cvsweb.cgi/src/winsup/cygwin/include/mqueue.h?cvsroot=src
    mq_max_messages = None

    # Try to get the value from where Linux stores it.
    try:
        mq_max_messages = int(open("/proc/sys/fs/mqueue/msg_max").read())
    except:
        # Oh well.
        pass

    if not mq_max_messages:
        # Maybe we're on BSD.
        mq_max_messages = get_sysctl_value('kern.mqueue.maxmsg')
        if mq_max_messages:
            mq_max_messages = int(mq_max_messages)

    if not mq_max_messages:
        # We're on a non-Linux, non-BSD system, or OS X, or BSD with
        # the mqueuefs kernel module not loaded (which it's not, by default,
        # under FreeBSD 8.x and 9.x which are the only systems I've tested).
        #
        # If we're on FreeBSD and mqueuefs isn't loaded when this code runs,
        # sysctl won't be able to provide mq_max_messages to me. (I assume other
        # BSDs behave the same.) If I use too large of a default, then every
        # attempt to create a message queue via posix_ipc will fail with
        # "ValueError: Invalid parameter(s)"  unless the user explicitly sets
        # the max_messages param.
        if platform.system().endswith("BSD"):
            # 100 is the value I see under FreeBSD 9.2. I hope this works
            # elsewhere!
            mq_max_messages = 100
        else:
            # We're on a non-Linux, non-BSD system. I take a wild guess at an
            # appropriate value. The max possible is > 2 billion, but the
            # values used by Linux and FreeBSD suggest that a smaller default
            # is wiser.
            mq_max_messages = 1024

    return mq_max_messages


def sniff_mq_max_message_size_default():
    # The max message size is not defined by POSIX.

    # On most systems I've tested, msg Qs are implemented via mmap-ed files
    # or a similar interface, so the only theoretical limits are imposed by
    # the file system. In practice, Linux and *BSD impose some tighter limits.

    # On Linux, max message size is available in a /proc file and often
    # defaults to the value of 8192.

    # On FreeBSD (and other BSDs, I assume), it's available via sysctl as
    # kern.mqueue.maxmsgsize. On my FreeBSD 9.1 test system, it defaults to
    # 16384.

    # mqueue.h defines mq_attr.mq_msgsize as a C long, so that's
    # a practical limit for this value.

    # Further complicating things is the fact that the module has to allocate
    # a buffer the size of the queue's max message every time receive() is
    # called, so it would be a bad idea to set this default to the max.
    # I set it to 8192 -- not too small, not too big. I only set it smaller
    # if I'm on a system that tells me I must do so.
    DEFAULT = 8192
    mq_max_message_size_default = 0

    # Try to get the value from where Linux stores it.
    try:
        mq_max_message_size_default = \
                            int(open("/proc/sys/fs/mqueue/msgsize_max").read())
    except:
        # oh well
        pass

    if not mq_max_message_size_default:
        # Maybe we're on BSD.
        mq_max_message_size_default = get_sysctl_value('kern.mqueue.maxmsgsize')
        if mq_max_message_size_default:
            mq_max_message_size_default = int(mq_max_message_size_default)

    if not mq_max_message_size_default:
        mq_max_message_size_default = DEFAULT

    return mq_max_message_size_default


def discover():
    linker_options = ""
    d = {}

    f = open("VERSION")
    d["POSIX_IPC_VERSION"] = '"%s"' % f.read().strip()
    f.close()

    # Sniffing of the realtime libs has to go early in the list so as
    # to provide correct linker options to the rest of the tests.
    if "Darwin" in platform.uname():
        # I skip the test under Darwin/OS X for two reasons. First, I know
        # it isn't needed there. Second, I can't even compile the test for
        # the realtime lib because it references mq_unlink() which OS X
        # doesn't support. Unfortunately sniff_realtime_lib.c *must*
        # reference mq_unlink() or some other mq_xxx() function because
        # it is only the message queues that need the realtime libs under
        # FreeBSD.
        realtime_lib_is_needed = False
    else:
        # Some platforms (e.g. Linux & OpenSuse) require linking to librt
        realtime_lib_is_needed = sniff_realtime_lib()

    if realtime_lib_is_needed:
        d["REALTIME_LIB_IS_NEEDED"] = ""
        linker_options = " -lrt "

    d["PAGE_SIZE"] = sniff_page_size()

    if sniff_sem_getvalue(linker_options):
        d["SEM_GETVALUE_EXISTS"] = ""

    if ("SEM_GETVALUE_EXISTS" in d) and ("Darwin" in platform.uname()):
        # sem_getvalue() isn't available on OS X. The function exists but
        # always returns -1 (under OS X 10.9) or ENOSYS ("Function not
        # implemented") under some earlier version(s).
        del d["SEM_GETVALUE_EXISTS"]

    if sniff_sem_timedwait(linker_options):
        d["SEM_TIMEDWAIT_EXISTS"] = ""

    d["SEM_VALUE_MAX"] = sniff_sem_value_max()
    # A return of None means that I don't need to #define this myself.
    if d["SEM_VALUE_MAX"] is None:
        del d["SEM_VALUE_MAX"]

    if sniff_mq_existence(linker_options):
        d["MESSAGE_QUEUE_SUPPORT_EXISTS"] = ""

    d["QUEUE_MESSAGES_MAX_DEFAULT"] = sniff_mq_max_messages()
    d["QUEUE_MESSAGE_SIZE_MAX_DEFAULT"] = sniff_mq_max_message_size_default()
    d["QUEUE_PRIORITY_MAX"] = sniff_mq_prio_max()

    msg = """/*
This header file was generated when you ran setup. Once created, the setup
process won't overwrite it, so you can adjust the values by hand and
recompile if you need to.

On your platform, this file may contain only this comment -- that's OK!

To enable lots of debug output, add this line and re-run setup.py:
#define POSIX_IPC_DEBUG

To recreate this file, just delete it and re-run setup.py.
*/

"""
    filename = "./src/system_info.h"
    if not os.path.exists(filename):
        lines = ["#define %s\t\t%s" % (key, d[key]) for key in d if key != "PAGE_SIZE"]

        # PAGE_SIZE gets some special treatment. It's defined in header files
        # on some systems in which case I might get a redefinition error in
        # my header file, so I wrap it in #ifndef/#endif.

        lines.append("#ifndef PAGE_SIZE")
        lines.append("#define PAGE_SIZE\t\t%s" % d["PAGE_SIZE"])
        lines.append("#endif")

        # A trailing '\n' keeps compilers happy...
        open(filename, "w").write(msg + '\n'.join(lines) + '\n')

    return d


if __name__ == "__main__":
    print(discover())
