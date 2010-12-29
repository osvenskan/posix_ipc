#include <mqueue.h>
#include <stdlib.h>

int main(void) { 
    mq_unlink(NULL);
    
    return 0;
}

