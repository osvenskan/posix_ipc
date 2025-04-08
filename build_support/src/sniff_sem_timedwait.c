#include <stdlib.h>
#include <semaphore.h>

int main(void) { 
    sem_timedwait(NULL, NULL);
    return 0; 
}

