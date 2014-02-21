#include <stdlib.h>
#include <stdio.h>
#include <semaphore.h>
#include <errno.h> 
#include <fcntl.h>

/* This is a program for testing whether or not OSX supports sem_getvalue()
yet. Use this to compile --
   cc -Wall -o foo sem_getvalue_test.c -lpthread

If sem_getvalue() is not supported, you'll get something like this --
   sem_getvalue() returned -1, the semaphore's value is -99

If sem_getvalue() is supported (e.g. on Linux), you'll get this --
   sem_getvalue() returned 0, the semaphore's value is 1

*/

int main(void) { 
	int rc;
	int sem_value = -99;  // Init to nonsense value

    sem_t *pSemaphore = NULL;

	pSemaphore = sem_open("/my_semaphore", O_CREAT, 0600, 0);

    if (pSemaphore == SEM_FAILED)
        printf("Creating the semaphore failed; errno is %d\n", errno);


    rc = sem_post(pSemaphore);
    if (rc)
        printf("Releasing the semaphore failed; errno is %d\n", errno);

    rc = sem_getvalue(pSemaphore, &sem_value);
    printf("sem_getvalue() returned %d, the semaphore's value is %d\n", 
    	   rc, sem_value);


    
    rc = sem_wait(pSemaphore);
    if (rc)
        printf("Acquiring the semaphore failed; errno is %d\n", errno);
        

	rc = sem_close(pSemaphore);

    return 0; 
}

