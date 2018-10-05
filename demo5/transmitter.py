import posix_ipc

# This program opens the message queue and sends a message

mq = posix_ipc.MessageQueue("/python_ipc_test")
mq.block = False

mq.send("From transmitter")
