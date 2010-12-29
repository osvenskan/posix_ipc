import posix_ipc
import pdb

#mq = posix_ipc.MessageQueue("/foo", posix_ipc.O_CREX, 0600, 5, 4096)
sem = posix_ipc.Semaphore("/fook", posix_ipc.O_CREX, 0600, 1)
 
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
#mq.request_notification(THE_SIGNAL)

pdb.set_trace()


i=42

#sem = sem
#shm = shm

# shm.unlink()
# 
sem.close()
sem.unlink()
 
# mq.close()
# mq.unlink()

