#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <semaphore.h>
#include <string.h>

#include "utils.h"
#include "md5.h"


void md5ify(char *inString, char *outString) {
	md5_state_t state;
	md5_byte_t digest[16];
    int i;
    
	md5_init(&state);
	md5_append(&state, (const md5_byte_t *)inString, strlen(inString));
	md5_finish(&state, digest);

    for (i = 0; i < 16; i++)
        sprintf(&outString[i * 2], "%02x", digest[i]);
}

void say(const char *pName, char *pMessage) {
    time_t the_time;
    struct tm *the_localtime;
    char timestamp[256];
    
    the_time = time(NULL);
    
    the_localtime = localtime(&the_time);
    
    strftime(timestamp, 255, "%H:%M:%S", the_localtime);
    
    printf("%s @ %s: %s\n", pName, timestamp, pMessage);
    
}


int release_semaphore(const char *pName, sem_t *pSemaphore, int live_dangerously) {
    int rc = 0;
    char s[1024];
    
    say(pName, "Releasing the semaphore.");
    
    if (!live_dangerously) {
        rc = sem_post(pSemaphore);
        if (rc) {
            sprintf(s, "Releasing the semaphore failed; errno is %d\n", errno);
            say(pName, s);
        }
    }
    
    return rc;
}


int acquire_semaphore(const char *pName, sem_t *pSemaphore, int live_dangerously) {
    int rc = 0;
    char s[1024];

    say(pName, "Waiting to acquire the semaphore.");

    if (!live_dangerously) {
        rc = sem_wait(pSemaphore);
        if (rc) {
            sprintf(s, "Acquiring the semaphore failed; errno is %d\n", errno);
            say(pName, s);
        }
    }

    return rc;
}


void read_params(struct param_struct *params) {
    char line[1024];
    char name[1024];
    char value[1024];
    
    FILE *fp;
    
    fp = fopen("params.txt", "r");
    
    while (fgets(line, 1024, fp)) {
        if (strlen(line) && ('#' == line[0]))
            ; // comment in input, ignore
        else {
            sscanf(line, "%[ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghjiklmnopqrstuvwxyz]=%s\n", name, value);
        
            // printf("name = %s, value = %d\n", name, value);

            if (!strcmp(name, "ITERATIONS"))
                params->iterations = atoi(value);
            if (!strcmp(name, "LIVE_DANGEROUSLY"))
                params->live_dangerously = atoi(value);
            if (!strcmp(name, "SEMAPHORE_NAME"))
                strcpy(params->semaphore_name, value);
            if (!strcmp(name, "SHARED_MEMORY_NAME"))
                strcpy(params->shared_memory_name, value);
            if (!strcmp(name, "PERMISSIONS"))
                params->permissions = (int)strtol(value, NULL, 8);
            if (!strcmp(name, "SHM_SIZE"))
                params->size = atoi(value);
                
            name[0] = '\0';
            value[0] = '\0';
        }
    }
    
    printf("iterations = %d\n", params->iterations);
    printf("danger = %d\n", params->live_dangerously);
    printf("semaphore name = %s\n", params->semaphore_name);
    printf("shared memory name = %s\n", params->shared_memory_name);
    printf("permissions = %o\n", params->permissions);
    printf("size = %d\n", params->size);
}
