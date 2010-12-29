This demonstrates use of message queues via two applications named after
Mrs. Premise and Mrs. Conclusion of the Monty Python sketch. 
http://www.youtube.com/watch?v=crIJvcWkVcs

Like those two characters, these programs chat back and forth and the result 
is a lot of nonsense. In this case, what the programs are saying isn't the
interesting part. What's interesting is how they're doing it.

Mrs. Premise and Mrs. Conclusion (the programs, not the sketch characters)
communicate with POSIX message queues.

Mrs. Premise starts things off by creating the queue and sending a random 
string (the current time) to it. She then sits in a loop receiving whatever 
message is on the queue. If it is the same message she wrote, she sends it
back to the queue. If it is a new message, it must be from Mrs. Conclusion.

Meanwhile, Mrs. Conclusion is doing exactly the same thing, except that she
assumes Mrs. Premise will write the first message.

When either of these programs receives a new message, they send back an
md5 hash of that message. This serves two purposes. First, it ensures that
subsequent messages are very different so that if a message somehow gets
corrupted (say by being partially overwritten by the next message), it will
not escape notice. Second, it ensures that corruption can be detected if
it happens, because Mrs. Premise and Mrs. Conclusion can calculate what the
other's response to their message should be.

Since message queues manage all of the concurrency issues transparently,
Mrs. Premise and Mrs. Conclusion won't ever find their messages corrupted
no matter how many messages they exchange. You can experiment with this by 
setting ITERATIONS in params.txt to a very large value.

These programs are not meant as a demostration on how to make best use of a 
message queue. In fact, they're very badly behaved because they poll the
queue as fast as possible -- they'll send your CPU usage right up to 100%.
Remember, they're trying as hard as they can to step one another so as to 
expose any concurrency problems that might be present. 

Real code would want to sleep (or do something useful) in between calling
send() and receive(). 

