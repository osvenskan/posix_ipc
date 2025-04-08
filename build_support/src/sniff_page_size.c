#include <stdio.h>

// Code for determining page size swiped from Python's mmapmodule.c
#if defined(HAVE_SYSCONF) && defined(_SC_PAGESIZE)
static int
my_getpagesize(void)
{
	return sysconf(_SC_PAGESIZE);
}
#else
#include <unistd.h>
#define my_getpagesize getpagesize
#endif

int main(void) { 
    printf("%d\n", my_getpagesize());
    
    return 0; 
}
