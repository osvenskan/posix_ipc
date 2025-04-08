import posix_ipc
import utils

try:
    posix_ipc.unlink_message_queue(utils.QUEUE_NAME)
    s = "message queue %s removed" % utils.QUEUE_NAME
    print(s)
except:
    print("queue doesn't need cleanup")

print("\nAll clean!")
