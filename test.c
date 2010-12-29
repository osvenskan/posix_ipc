#include <string.h> 
#include <stdio.h> 
#include <stdlib.h> 
#include <errno.h> 
#include <time.h>

static int 
random_in_range(int min, int max) {
    // returns a random int N such that min <= N <= max
    int diff = (max - min) + 1;
    
    // ref: http://www.c-faq.com/lib/randrange.html
    return ((int)((double)rand() / ((double)RAND_MAX + 1) * diff)) + min;
}

// 
// static int 
// random_in_range() {
//     return ((int)((double)rand() / ((double)RAND_MAX + 1) * 25)) + 1;
// }


static 
int create_random_name(char *name) {
    // The random name is always lowercase so that this code will work
    // on case-insensitive file systems. It always starts with a forward
    // slash. 
    int length;
    char *alphabet = "abcdefghijklmnopqrstuvwxyz";
    int i;
    
    // Generate a random length for the name. I subtract 1 from the 
    // MAX_SAFE_NAME_LENGTH in order to allow for the name's leading "/".
    length = random_in_range(6, 14 - 1);
    
    //DPRINTF("Random name length = %d\n", length);
    
    name[0] = '/';
    name[length] = '\0';
    i = length;
    while (--i) 
        name[i] = alphabet[random_in_range(0, 25)];

    //DPRINTF("Random name = %s\n", name);
    
    return length;
}


int main() { 
    int i;
    char name[14 + 1];
    //char *foo = "abc";
    
    
    //printf("%d\n", (int)strlen(foo));
    
    
    srand((unsigned int)time(NULL));
    
    for (i = 0; i < 1000000; i++) {
        //printf("%d\n", random_in_range(3, 92));
        //printf("%d\n", random_in_range());
        create_random_name(name);
        printf("%s\n", name);
        memset(name, '~', 14 + 1);
        
    }
    
    return 0;

}