# -*- coding: utf-8 -*-


import posix_ipc
import random
# import sys
# 
# PY_MAJOR_VERSION = sys.version_info[0]
# 
# print (PY_MAJOR_VERSION)

def say(s):
    """A wrapper for print() that's compatible with Python 2 & 3"""
    print (s)

def random_string(length):
    return ''.join(random.sample("abcdefghijklmnopqrstuvwxyz", length))



mq = posix_ipc.MessageQueue("/p_ipc_test", posix_ipc.O_CREAT)

#s = random_string(15)
s = "förändra"
print(len(s.encode("utf-8")))
# print(type(s))
# print(type(s.encode("utf-8")))
s = s.encode("utf-8")
mq.send(s)
z = mq.receive()
import pdb
pdb.set_trace()

mq.close()
mq.unlink()
