import time
import sys

PY_MAJOR_VERSION = sys.version_info[0]

if PY_MAJOR_VERSION > 2:
    NULL_CHAR = 0
else:
    NULL_CHAR = '\0'


def raise_error(error, message):
    # I have to exec() this code because the Python 2 syntax is invalid
    # under Python 3 and vice-versa.
    s = "raise "
    s += "error, message" if (PY_MAJOR_VERSION == 2) else "error(message)"

    exec(s)


def say(s):
    """Prints a timestamped, self-identified message"""
    who = sys.argv[0]
    if who.endswith(".py"):
        who = who[:-3]

    s = "%s@%1.6f: %s" % (who, time.time(), s)
    print(s)


def write_to_memory(mapfile, s):
    """Writes the string s to the mapfile"""
    say("writing %s " % s)
    mapfile.seek(0)
    # I append a trailing NULL in case I'm communicating with a C program.
    s += '\0'
    if PY_MAJOR_VERSION > 2:
        s = s.encode()
    mapfile.write(s)


def read_from_memory(mapfile):
    """Reads a string from the mapfile and returns that string"""
    mapfile.seek(0)
    s = []
    c = mapfile.read_byte()
    while c != NULL_CHAR:
        s.append(c)
        c = mapfile.read_byte()

    if PY_MAJOR_VERSION > 2:
        s = [chr(c) for c in s]
    s = ''.join(s)

    say("read %s" % s)

    return s


def read_params():
    """Reads the contents of params.txt and returns them as a dict"""
    params = {}

    f = open("params.txt")

    for line in f:
        line = line.strip()
        if line:
            if line.startswith('#'):
                pass  # comment in input, ignore
            else:
                name, value = line.split('=')
                name = name.upper().strip()

                if name == "PERMISSIONS":
                    # Think octal, young man!
                    value = int(value, 8)
                elif "NAME" in name:
                    # This is a string; leave it alone.
                    pass
                else:
                    value = int(value)

                # print "name = %s, value = %d" % (name, value)

                params[name] = value

    f.close()

    return params
