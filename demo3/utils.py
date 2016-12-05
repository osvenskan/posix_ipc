# Python modules
import sys


QUEUE_NAME = "/my_message_queue"


PY_MAJOR_VERSION = sys.version_info[0]


def get_input():
    """Get input from user, Python 2.x and 3.x compatible"""
    if PY_MAJOR_VERSION > 2:
        return input()
    else:
        return raw_input()
