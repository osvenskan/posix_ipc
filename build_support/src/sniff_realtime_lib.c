#include <mqueue.h>

int main(void) { 
    /* Under FreeBSD and OpenSuse, linking to the realtime lib is required, 
       but only for mq_xxx() functions so checking for sem_xxx() or shm_xxx() 
       here is not be a sufficient test.
    */
    mq_unlink(""); 

    return 0;
}
