#include <stdio.h> 
#include <errno.h> 
#include <unistd.h> 
#include <string.h>
#include <time.h>
#include <semaphore.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <stdarg.h>

#include "md5.h"
#include "utils.h"

const char MY_NAME[] = "Mrs. Premise";

// Set up a Mrs. Premise & Mrs. Conclusion conversation.

void get_current_time(char *);

int main() { 
    sem_t *pSemaphore = NULL;
    int rc;
    char s[1024];
    void *pSharedMemory = NULL;
    char last_message_i_wrote[256];
    char md5ified_message[256];
    int i = 0;
    int done = 0;
    int fd;
    struct param_struct params;
    
    say(MY_NAME, "Oooo 'ello, I'm Mrs. Premise!");
    
    read_params(&params);

    // Create the shared memory
    fd = shm_open(params.shared_memory_name, O_RDWR | O_CREAT | O_EXCL, params.permissions);
    
    if (fd == -1) {
        fd = 0;
        sprintf(s, "Creating the shared memory failed; errno is %d", errno);
        say(MY_NAME, s);
    }
    else {
        // The memory is created as a file that's 0 bytes long. Resize it.
        rc = ftruncate(fd, params.size);
        if (rc) {
            sprintf(s, "Resizing the shared memory failed; errno is %d", errno);
            say(MY_NAME, s);
        }
        else {
            // MMap the shared memory
            //void *mmap(void *start, size_t length, int prot, int flags, int fd, off_t offset);
            pSharedMemory = mmap((void *)0, (size_t)params.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
            if (pSharedMemory == MAP_FAILED) {
                pSharedMemory = NULL;
                sprintf(s, "MMapping the shared memory failed; errno is %d", errno);
                say(MY_NAME, s);
            }
            else {
                sprintf(s, "pSharedMemory = %p", pSharedMemory);
                say(MY_NAME, s);
            }
        }
    }
    
    if (pSharedMemory) {
        // Create the semaphore
        pSemaphore = sem_open(params.semaphore_name, O_CREAT, params.permissions, 0);
    
        if (pSemaphore == SEM_FAILED) {
            sprintf(s, "Creating the semaphore failed; errno is %d", errno);
            say(MY_NAME, s);
        }
        else {
            sprintf(s, "the semaphore is %p", (void *)pSemaphore);
            say(MY_NAME, s);
        
            // I seed the shared memory with a random string (the current time).
            get_current_time(s);
    
            strcpy((char *)pSharedMemory, s);
            strcpy(last_message_i_wrote, s);

            sprintf(s, "Wrote %zu characters: %s", strlen(last_message_i_wrote), last_message_i_wrote);
            say(MY_NAME, s);
            
            i = 0;
            while (!done) {
                sprintf(s, "iteration %d", i);
                say(MY_NAME, s);

                // Release the semaphore...
                rc = release_semaphore(MY_NAME, pSemaphore, params.live_dangerously);
                // ...and wait for it to become available again. In real code 
                // I might want to sleep briefly before calling .acquire() in
                // order to politely give other processes an opportunity to grab
                // the semaphore while it is free so as to avoid starvation. But 
                // this code is meant to be a stress test that maximizes the 
                // opportunity for shared memory corruption and politeness is 
                // not helpful in stress tests.
                if (!rc)
                    rc = acquire_semaphore(MY_NAME, pSemaphore, params.live_dangerously);

                if (rc)
                    done = 1;
                else {
                    // I keep checking the shared memory until something new has 
                    // been written.
                    while ( (!rc) && \
                            (!strcmp((char *)pSharedMemory, last_message_i_wrote)) 
                          ) {
                        // Nothing new; give Mrs. Conclusion another change to respond.
                        sprintf(s, "Read %zu characters '%s'", strlen((char *)pSharedMemory), (char *)pSharedMemory);
                        say(MY_NAME, s);
                        rc = release_semaphore(MY_NAME, pSemaphore, params.live_dangerously);
                        if (!rc) {
                            rc = acquire_semaphore(MY_NAME, pSemaphore, params.live_dangerously);
                        }
                    }


                    if (rc) 
                        done = 1;
                    else {
                        // What I read must be the md5 of what I wrote or something's 
                        // gone wrong.
                        md5ify(last_message_i_wrote, md5ified_message);
                    
                        if (strcmp(md5ified_message, (char *)pSharedMemory) == 0) {
                            // Yes, the message is OK
                            i++;
                            if (i == params.iterations)
                                done = 1;

                            // MD5 the reply and write back to Mrs. Conclusion.
                            md5ify(md5ified_message, md5ified_message);
                            
                            sprintf(s, "Writing %zu characters '%s'", strlen(md5ified_message), md5ified_message);
                            say(MY_NAME, s);

                            strcpy((char *)pSharedMemory, md5ified_message);
                            strcpy((char *)last_message_i_wrote, md5ified_message);
                        }
                        else {
                            sprintf(s, "Shared memory corruption after %d iterations.", i);
                            say(MY_NAME, s);                            
                            sprintf(s, "Mismatch; new message is '%s', expected '%s'.", (char *)pSharedMemory, md5ified_message);
                            say(MY_NAME, s);
                            done = 1;
                        }
                    }
                }
            }

            // Announce for one last time that the semaphore is free again so that 
            // Mrs. Conclusion can exit.
            say(MY_NAME, "Final release of the semaphore followed by a 5 second pause");            
            rc = release_semaphore(MY_NAME, pSemaphore, params.live_dangerously);
            sleep(5);
            // ...before beginning to wait until it is free again. 
            // Technically, this is bad practice. It's possible that on a 
            // heavily loaded machine, Mrs. Conclusion wouldn't get a chance
            // to acquire the semaphore. There really ought to be a loop here
            // that waits for some sort of goodbye message but for purposes of
            // simplicity I'm skipping that.

            say(MY_NAME, "Final wait to acquire the semaphore");
            rc = acquire_semaphore(MY_NAME, pSemaphore, params.live_dangerously);
            if (!rc) {
                say(MY_NAME, "Destroying the shared memory.");

                // Un-mmap the memory...
                rc = munmap(pSharedMemory, (size_t)params.size);
                if (rc) {
                    sprintf(s, "Unmapping the memory failed; errno is %d", errno);
                    say(MY_NAME, s);
                }
                
                // ...close the file descriptor...
                if (-1 == close(fd)) {
                    sprintf(s, "Closing the memory's file descriptor failed; errno is %d", errno);
                    say(MY_NAME, s);
                }
            
                // ...and destroy the shared memory.
                rc = shm_unlink(params.shared_memory_name);
                if (rc) {
                    sprintf(s, "Unlinking the memory failed; errno is %d", errno);
                    say(MY_NAME, s);
                }
            }
        }

        say(MY_NAME, "Destroying the semaphore.");
        // Clean up the semaphore
        rc = sem_close(pSemaphore);
        if (rc) {
            sprintf(s, "Closing the semaphore failed; errno is %d", errno);
            say(MY_NAME, s);
        }
        rc = sem_unlink(params.semaphore_name);
        if (rc) {
            sprintf(s, "Unlinking the semaphore failed; errno is %d", errno);
            say(MY_NAME, s);
        }
    }
    return 0; 
}


void get_current_time(char *s) {
    time_t the_time;
    struct tm *the_localtime;
    char *pAscTime;

    the_time = time(NULL);
    the_localtime = localtime(&the_time);
    pAscTime = asctime(the_localtime);
    
    strcpy(s, pAscTime);
}
