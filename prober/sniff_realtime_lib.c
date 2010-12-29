#include <semaphore.h>
#include <stdlib.h>

int main(void) { 
    /* Under FreeBSD, linking to the realtime lib is required, but only
       for mq_xxx() functions so checking for sem_xxx() or shm_xxx() here
       would not be a sufficient test.
    */
    mq_unlink(NULL); 

    return 0;
}
