Demonstration of using message queues together with the `selectors` module in Python.

The `selectors` module provides high-level I/O multiplexing akin to an event
library -- in brief, various event source, such as file handlers, sockets,
message queues, can be registered with an event selector, which then returns
if any event is triggered.

The low-level functionality is OS specific and more information is available in
the Python documentation.

The example consists of two Python files: listener.py and tranmitter.py

The listener creates a message queues and waits for events using the
`selectors` module. When the transmitter program is run, a message is sent
and the listener will print the content.

Procedure:

 1. Run listener.py
 2. Run transmitter.py (in a new terminal)
 3. Observe that listener has printed and exited

Note that listener.py MUST be run first.
