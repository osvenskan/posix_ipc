import subprocess
import platform
import os
import shlex

# Set these to None for compile/link debugging or subprocess.PIPE to silence
# compiler warnings and errors.
STDOUT = subprocess.PIPE
STDERR = subprocess.PIPE
# STDOUT = None
# STDERR = None


# OUTPUT_FILEPATH is the file that this script will write, if necessary. The path is relative
# to the project root. Setuptools guarantees that the project root will be the current working
# directory when this script executes.
OUTPUT_FILEPATH = "./src/system_info.h"


# A few behaviors depend on whether or not this runs on a Mac.
IS_MAC = ("Darwin" in platform.uname())


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
    '''Returns True if the file compiles and links successfully, False otherwise.

    It can be perfectly normal for the build to fail, e.g. when building sniff_sem_getvalue.c on
    a system where sem_getvalue() doesn't exist.

    Note that unlike compile_and_run(), this just builds an executable. It does not attempt to
    run that executable.
    '''
    # There are two things to note about the command --
    #   - If there's a linker option like -lrt, it needs to come *after*
    #     the specification of the C file or linking will fail on Ubuntu 11.10
    #     (maybe because of the gcc version?)
    #   - Some versions of Linux place the sem_xxx() functions in libpthread.
    #     Rather than testing whether or not it's needed, I just specify it
    #     everywhere since it's harmless to specify it when it's not needed.
    cc = os.getenv("CC", "cc")
    cmd = [
           *shlex.split(cc),
           '-Wall',
           '-o',
           f'./build_support/src/{filename[:-2]}',
           f'./build_support/src/{filename}',
           linker_options,
           '-lpthread'
           ]
    p = subprocess.Popen(cmd, stdout=STDOUT, stderr=STDERR)

    # p.wait() returns the process' return code, so 0 implies that
    # the compile & link succeeded.
    return not bool(p.wait())


def compile_and_run(filename, linker_options=""):
    '''Compiles and links the file, runs the executable, and returns whatever the executable
    prints to stdout.

    Failure of any of the steps (compile, link, run) is unexepected. This function returns None
    in that case.
    '''
    if does_build_succeed(filename, linker_options):
        cmd = f"./build_support/src/{filename[:-2]}"
        try:
            s = subprocess.Popen([cmd], stdout=subprocess.PIPE).communicate()[0]
            return s.strip().decode()
        except Exception:
            # Execution resulted in an error. This is unexpected.
            return None
    else:
        # Build resulted in an error. This is unexpected.
         return None


def get_sysctl_value(name):
    """Given a sysctl name (e.g. 'kern.mqueue.maxmsg'), returns sysctl's value for that variable
    or None if the sysctl call fails (unknown name, sysctl not supported, etc.)
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
    except Exception:
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
    '''Returns True if sem_getvalue() works on this system, False otherwise.'''
    if IS_MAC:
        # On the Mac, sem_getvalue() exists but always returns -1 (under OS X ≥ 10.9) or
        # ENOSYS ("Function not implemented") under some earlier version(s). It's a waste of
        # time to look for it on that platform.
        return False
    else:
        return does_build_succeed("sniff_sem_getvalue.c", linker_options)


def sniff_sem_timedwait(linker_options):
    '''Returns True if sem_timedwait() works on this system, False otherwise.'''
    return does_build_succeed("sniff_sem_timedwait.c", linker_options)


def sniff_sem_value_max():
    '''Returns either None, or a value suitable for inclusion in system_info.h.'''
    # The max semaphore value should be present in sysconf() on POSIX-compliant systems.
    sem_value_max = maybe_get_sysconf_value('SC_SEM_VALUE_MAX', True)

    if not sem_value_max:
        # This value of last resort should be #defined everywhere. What
        # could possibly go wrong?
        sem_value_max = "_POSIX_SEM_VALUE_MAX"

    return sem_value_max


def sniff_page_size():
    '''Returns the page size (usually 4096 or 16384) suitable for inclusion in system_info.h.

    Raises a DiscoveryError exception if unable to determine the page size.
    '''
    page_size = None

    # When cross compiling under cibuildwheel, I need to rely on their custom env var to set the
    # page size correctly. See https://github.com/osvenskan/posix_ipc/issues/58
    if 'arm' in os.getenv('_PYTHON_HOST_PLATFORM', ''):
        page_size = 16384

    if not page_size:
        # Page size should be present in sysconf() on POSIX-compliant systems, and checking
        # sysconf is easier than invoking the compiler.
        page_size = maybe_get_sysconf_value('SC_PAGESIZE', True)

    if not page_size:
        # OK, I have to do it the hard way. I don't need to worry about linker options here
        # because I'm not calling any functions, just getting the value of a #define.
        page_size = compile_and_run("sniff_page_size.c")

    if not page_size:
        raise DiscoveryError('Unable to determine page size')

    return page_size


def sniff_mq_existence(linker_options):
    '''Returns True if the system supports message queues, False otherwise.'''
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


def sniff_mq_max_messages_default():
    '''Returns the value (in bytes) that will be used for the module constant
    QUEUE_MESSAGES_MAX_DEFAULT. This value is only used when creating a MessageQueue; it is the
    default value if the caller doesn't supply one.

    The value returned by this function is formatted for inclusion in system_info.h.

    Since this value is of minor consequence, I return a default value (instead of raising an error)
    if this function can't find a system-supplied value.
    '''
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
        with open("/proc/sys/fs/mqueue/msg_max") as f:
            mq_max_messages = int(f.read())
    except Exception:
        # Oh well.
        pass

    if not mq_max_messages:
        # Try sysctl
        mq_max_messages = get_sysctl_value('kern.mqueue.maxmsg')
        if mq_max_messages:
            mq_max_messages = int(mq_max_messages)

    if not mq_max_messages:
        # I take a wild guess at an appropriate value. The max possible is > 2 billion, but the
        # values used by Linux and FreeBSD suggest that a smaller default is wiser.
        mq_max_messages = 100

    return mq_max_messages


def sniff_mq_max_message_size_default():
    '''Returns the value (in bytes) that will be used for the module constant
    QUEUE_MESSAGE_SIZE_MAX_DEFAULT. This value is only used when creating a MessageQueue; it is the
    default value if the caller doesn't supply one.

    The value returned by this function is formatted for inclusion in system_info.h.

    Since this value is of minor consequence, I return a default value (instead of raising an error)
    if this function can't find a system-supplied value.
    '''
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
        with open("/proc/sys/fs/mqueue/msgsize_max") as f:
            mq_max_message_size_default = int(f.read())
    except Exception:
        # oh well
        pass

    if not mq_max_message_size_default:
        # Try sysctl
        mq_max_message_size_default = get_sysctl_value('kern.mqueue.maxmsgsize')
        if mq_max_message_size_default:
            mq_max_message_size_default = int(mq_max_message_size_default)

    if not mq_max_message_size_default:
        # Just use the default.
        mq_max_message_size_default = DEFAULT

    return mq_max_message_size_default


def discover():
    '''This is the main entry point for this script. It returns a dict of information it has
    discovered about the buld system. If system_info.h already exists when this script is
    invoked, then the returned dict consists only of one entry which describes whether or not
    posix_ipc needs to be linked to the realtime library.

    If system_info.h does not exist, this script creates and populates it, and the values in the
    returned dict are what it wrote to system_info.h.
    '''
    sys_info = {}

    # First things first -- I need to figure out whether or not the realtime library is needed.
    if IS_MAC:
        # I skip the test under Darwin/Mac/OS X for two reasons. First, I know it isn't needed
        # there. Second, I can't even compile the test for the realtime lib because it
        # references mq_unlink() which OS X doesn't support. Unfortunately sniff_realtime_lib.c
        # *must* reference mq_unlink() or some other mq_xxx() function, because only the message
        # queues need the realtime libs under FreeBSD.
        realtime_lib_is_needed = False
    else:
        # Some platforms (e.g. Linux) require linking to librt
        realtime_lib_is_needed = sniff_realtime_lib()

    sys_info['realtime_lib_is_needed'] = realtime_lib_is_needed

    linker_options = "-lrt" if realtime_lib_is_needed else ""

    if os.path.exists(OUTPUT_FILEPATH):
        # As guaranteed in building.md, this script is (mostly) a no-op if the output file already
        # exists.
        pass
    else:
        # system_info.h doesn't exist, so I need to figure out what values should go into it.

        # Version info is easy. :-)
        with open("VERSION") as f:
            sys_info["POSIX_IPC_VERSION"] = f'"{f.read().strip()}"'

        # Figure out the page size.
        sys_info["PAGE_SIZE"] = sniff_page_size()

        # Sniff sem_getvalue()
        if sniff_sem_getvalue(linker_options):
            sys_info["SEM_GETVALUE_EXISTS"] = ""

        # Sniff sem_timedwait()
        if sniff_sem_timedwait(linker_options):
            sys_info["SEM_TIMEDWAIT_EXISTS"] = ""

        # Sniff the max value of a semaphore.
        sys_info["SEM_VALUE_MAX"] = sniff_sem_value_max()

        # Figure out if message queues are supported at all.
        message_queue_support_exists = sniff_mq_existence(linker_options)

        if message_queue_support_exists:
            sys_info["MESSAGE_QUEUE_SUPPORT_EXISTS"] = ""
            sys_info["QUEUE_MESSAGES_MAX_DEFAULT"] = sniff_mq_max_messages_default()
            sys_info["QUEUE_MESSAGE_SIZE_MAX_DEFAULT"] = sniff_mq_max_message_size_default()
            sys_info["QUEUE_PRIORITY_MAX"] = sniff_mq_prio_max()

        # Turn each of the values in sys_info into lines that will be written to system_info.h
        # PAGE_SIZE and SEM_VALUE_MAX get special handling, and realtime_lib_is_needed doesn't
        # need to go in the header file.
        ignore = ("PAGE_SIZE", "SEM_VALUE_MAX", "realtime_lib_is_needed")
        lines = [f"#define {key} {value}" for key, value in sys_info.items() if key not in ignore]

        # PAGE_SIZE gets some special treatment. It's defined in header files
        # on some systems in which case I might get a redefinition error in
        # my header file, so I wrap it in #ifndef/#endif.
        lines.append("#ifndef PAGE_SIZE")
        lines.append(f"#define PAGE_SIZE {sys_info['PAGE_SIZE']}")
        lines.append("#endif")
        # Ditto for SEM_VALUE_MAX.
        lines.append("#ifndef SEM_VALUE_MAX")
        lines.append(f"#define SEM_VALUE_MAX {sys_info['SEM_VALUE_MAX']}")
        lines.append("#endif")
        # A trailing blank line keeps compilers happy.
        lines.append('')

        msg = """/*
This header file was generated by discover_system_info.py. You can delete it,
edit it, or even write your own. See building.md for details.
*/

"""
        with open(OUTPUT_FILEPATH, 'w') as f:
            f.write(msg + '\n'.join(lines))

    return sys_info


if __name__ == "__main__":
    print(discover())
