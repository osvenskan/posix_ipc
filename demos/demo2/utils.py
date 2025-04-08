import time
import sys


def say(s):
    who = sys.argv[0]
    if who.endswith(".py"):
        who = who[:-3]

    s = "%s@%1.6f: %s" % (who, time.time(), s)
    print(s)


def read_params():
    params = {}

    f = open("params.txt")

    for line in f:
        line = line.strip()
        if len(line):
            if line.startswith('#'):
                pass  # comment in input, ignore
            else:
                name, value = line.split('=')
                name = name.upper().strip()

                if name == "PERMISSIONS":
                    value = int(value, 8)
                elif "NAME" in name:
                    # This is a string; leave it alone.
                    pass
                else:
                    value = int(value)

                # print("name = %s, value = %d" % (name, value))

                params[name] = value

    f.close()

    return params
