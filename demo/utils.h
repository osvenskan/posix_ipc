struct param_struct {
    int iterations;
    int live_dangerously;
    char semaphore_name[512];
    char shared_memory_name[512];
    int permissions;
    int size;
};


void md5ify(char *, char *);
void say(const char *, char *);
int acquire_semaphore(const char *, sem_t *, int);
int release_semaphore(const char *, sem_t *, int);
void read_params(struct param_struct *);



