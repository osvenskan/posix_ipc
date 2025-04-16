#include <stdio.h> 
#include <errno.h> 
#include <unistd.h> 
#include <string.h> 
#include <time.h>
#include <semaphore.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <fcntl.h>

#include "md5.h"
#include "utils.h"

static const char MY_NAME[] = "Mrs. Conclusion";

// Set up a Mrs. Premise & Mrs. Conclusion conversation.

int main() { 
    sem_t *the_semaphore = NULL;
    int rc;
    char s[1024];
    int i;
    int done;
    int fd;
    void *pSharedMemory = NULL;
    char last_message_i_wrote[256];
    char md5ified_message[256];
    struct param_struct params;
    
    say(MY_NAME, "Oooo 'ello, I'm Mrs. Conclusion!");

    read_params(&params);

    // Mrs. Premise has already created the semaphore and shared memory. 
    // I just need to get handles to them.
    the_semaphore = sem_open(params.semaphore_name, 0);
    
    if (the_semaphore == SEM_FAILED) {
        the_semaphore = NULL;
        sprintf(s, "Getting a handle to the semaphore failed; errno is %d", errno);
        say(MY_NAME, s);
    }
    else {
        // get a handle to the shared memory
        fd = shm_open(params.shared_memory_name, O_RDWR, params.permissions);
        
        if (fd == -1) {
            sprintf(s, "Couldn't get a handle to the shared memory; errno is %d", errno);
            say(MY_NAME, s);
        }
        else {
            // mmap it.
            pSharedMemory = mmap((void *)0, (size_t)params.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
            if (pSharedMemory == MAP_FAILED) {
                sprintf(s, "MMapping the shared memory failed; errno is %d", errno);
                say(MY_NAME, s);
            }
            else {
                sprintf(s, "pSharedMemory = %p", pSharedMemory);
                say(MY_NAME, s);

                i = 0;
                done = 0;
                last_message_i_wrote[0] = '\0';
                while (!done) {
                    sprintf(s, "iteration %d", i);
                    say(MY_NAME, s);

                    // Wait for Mrs. Premise to free up the semaphore.
                    rc = acquire_semaphore(MY_NAME, the_semaphore, params.live_dangerously);
                    if (rc)
                        done = 1;
                    else {
                        while ( (!rc) && \
                                (!strcmp((char *)pSharedMemory, last_message_i_wrote)) 
                              ) {
                            // Nothing new; give Mrs. Premise another change to respond.
                            sprintf(s, "Read %zu characters '%s'", strlen((char *)pSharedMemory), (char *)pSharedMemory);
                            say(MY_NAME, s);
                            say(MY_NAME, "Releasing the semaphore");
                            rc = release_semaphore(MY_NAME, the_semaphore, params.live_dangerously);
                            if (!rc) {
                                say(MY_NAME, "Waiting to acquire the semaphore");
                                rc = acquire_semaphore(MY_NAME, the_semaphore, params.live_dangerously);
                            }
                        }
                        
                        md5ify(last_message_i_wrote, md5ified_message);

                        // I always accept the first message (when i == 0)
                        if ( (i == 0) || (!strcmp(md5ified_message, (char *)pSharedMemory)) ) {
                            // All is well
                            i++;
                    
                            if (i == params.iterations)
                                done = 1;

                            // MD5 the reply and write back to Mrs. Premise.
                            md5ify((char *)pSharedMemory, md5ified_message);

                            // Write back to Mrs. Premise.
                            sprintf(s, "Writing %zu characters '%s'", strlen(md5ified_message), md5ified_message);
                            say(MY_NAME, s);

                            strcpy((char *)pSharedMemory, md5ified_message);

                            strcpy(last_message_i_wrote, md5ified_message);
                        }
                        else {
                            sprintf(s, "Shared memory corruption after %d iterations.", i);
                            say(MY_NAME, s);                            
                            sprintf(s, "Mismatch; rc = %d, new message is '%s', expected '%s'.", rc, (char *)pSharedMemory, md5ified_message);
                            say(MY_NAME, s);
                            done = 1;
                        }                        
                    }

                    // Release the semaphore.
                    rc = release_semaphore(MY_NAME, the_semaphore, params.live_dangerously);
                    if (rc)
                        done = 1;
                }
            }
            // Un-mmap the memory
            rc = munmap(pSharedMemory, (size_t)params.size);
            if (rc) {
                sprintf(s, "Unmapping the memory failed; errno is %d", errno);
                say(MY_NAME, s);
            }
            
            // Close the shared memory segment's file descriptor            
            if (-1 == close(fd)) {
                sprintf(s, "Closing memory's file descriptor failed; errno is %d", errno);
                say(MY_NAME, s);
            }
        }
        rc = sem_close(the_semaphore);
        if (rc) {
            sprintf(s, "Closing the semaphore failed; errno is %d", errno);
            say(MY_NAME, s);
        }
    }
                    
  
    return 0; 
}
