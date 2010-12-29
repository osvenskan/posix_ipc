import posix_ipc
import pdb
import signal
import threading
import time

THE_SIGNAL = posix_ipc.USER_SIGNAL_MIN + 3

def handler(signal_number, current_stack_frame):
    assert(signal_number == THE_SIGNAL)
    print "boing!"
    
    
def t2(z):
    print "I vill terminate you!"
    print str(z)
    
def the_thread():
    for i in range(0, 30):
        print "ding! (%d)" % i
        time.sleep(1)
    

# t = threading.Thread(target=the_thread)
# 
# t.start()
    
signal.signal(THE_SIGNAL, handler)

mq = posix_ipc.MessageQueue("/foo", posix_ipc.O_CREX, 0600, 5, 4096)


mq.request_notification(THE_SIGNAL)

for i in range(30):
    print "ding! (%d)" % i
    time.sleep(1)


mq.close()
mq.unlink()

# sem = posix_ipc.Semaphore("/fook", posix_ipc.O_CREX, 0600, 1)
# 
# shm = posix_ipc.SharedMemory("/foo", posix_ipc.O_CREX, 0600, 4096)
#shm = posix_ipc.SharedMemory("/foo", mode=0400)

# 
# value = sem.value
# 
# while value == sem.value:
#     value += 1
#     sem.release()
#     
#     print sem.value
# 
# 

#shm.read(offset=-1)



#shm.remove()


#mq.request_notification( (t2, { 'a' : 666 }) )
mq.request_notification(THE_SIGNAL)

pdb.set_trace()

time.sleep(20)

pdb.set_trace()


i=42

#sem = sem
#shm = shm

# shm.unlink()
# 
# sem.close()
# sem.unlink()
 
mq.close()
mq.unlink()