import posix_ipc
import utils

params = utils.read_params()

try:
    posix_ipc.unlink_shared_memory(params["SHARED_MEMORY_NAME"])
    s = "memory segment %s removed" % params["SHARED_MEMORY_NAME"]
    print(s)
except:
    print("memory doesn't need cleanup")


try:
    posix_ipc.unlink_semaphore(params["SEMAPHORE_NAME"])
    s = "semaphore %s removed" % params["SEMAPHORE_NAME"]
    print(s)
except:
    print("semaphore doesn't need cleanup")


print("\nAll clean!")
