This demonstrates use of shared memory and semaphores via two applications 
named after Mrs. Premise and Mrs. Conclusion of the Monty Python sketch. 
http://www.youtube.com/watch?v=crIJvcWkVcs

Like those two characters, these programs chat back and forth and the result 
is a lot of nonsense. In this case, what the programs are saying isn't the
interesting part. What's interesting is how they're doing it.

Mrs. Premise and Mrs. Conclusion (the programs, not the sketch characters)
communicate through POSIX shared memory with a semaphore to control access
to that memory.

Mrs. Premise starts things off by creating the shared memory and semaphore
and writing a random string (the current time) to the memory. She then sits
in a loop reading the memory. If it holds the same message she wrote, she
does nothing. If it is a new message, it must be from Mrs. Conclusion.

Meanwhile, Mrs. Conclusion is doing exactly the same thing, except that she
assumes Mrs. Premise will write the first message.

When either of these programs reads a new message, they write back an md5 
hash of that message. This serves two purposes. First, it ensures that
subsequent messages are very different so that if a message somehow gets
corrupted (say by being partially overwritten by the next message), it will
not escape notice. Second, it ensures that corruption can be detected if
it happens, because Mrs. Premise and Mrs. Conclusion can calculate what the
other's response to their message should be.

Since they use a semaphore to control access to the shared memory, Mrs. 
Premise and Mrs. Conclusion won't ever find their messages corrupted no
matter how many messages they exchange. You can experiment with this by
setting ITERATIONS in params.txt to a very large value. You can change 
LIVE_DANGEROUSLY (also in params.txt) to a non-zero value to tell Mrs. 
Premise and Mrs. Conclusion to run without using the semaphore. The shared
memory will probably get corrupted in fewer than 1000 iterations.

To run the demo, start Mrs. Premise first in one window and then run
Mrs. Conclusion in another. 


   The Fancy Version 
   =================

If you want to get fancy, you can play with C versions of Mrs. Premise and 
Mrs. Conclusion. The script make_all.sh will compile them for you. (Linux
users will need to edit the script and uncomment the line for the 
Linux-specific linker option.) 

The resulting executables are called premise and conclusion and work exactly 
the same as their Python counterparts. You can have the two C programs talk 
to one another, or you can have premise.py talk to the C version of 
conclusion...the possibilities are endless. (Actually, there are only four 
possible combinations but "endless" sounds better.)

