import posix_ipc
import utils

params = utils.read_params()

try:
    posix_ipc.unlink_message_queue(params["MESSAGE_QUEUE_NAME"])
    s = "message queue %s removed" % params["MESSAGE_QUEUE_NAME"]
    print(s)
except:
    print("queue doesn't need cleanup")

print("\nAll clean!")
