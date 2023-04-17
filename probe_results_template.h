/*
 * This file can be used as a starting point for creating a probe_results.h file,
 * in the case where probing the build system is not desirable, such as cross compile environment.
 * In order to skip the probe and use a manually created probe_results.h set the env var SKIP_BUILDSYSTEM_PROBE
*/

#define POSIX_IPC_VERSION	"1.1.x"
#define SEM_GETVALUE_EXISTS
#define SEM_TIMEDWAIT_EXISTS
#define MESSAGE_QUEUE_SUPPORT_EXISTS
#define QUEUE_MESSAGES_MAX_DEFAULT 10
#define QUEUE_MESSAGE_SIZE_MAX_DEFAULT 8192
#define QUEUE_PRIORITY_MAX 32767U
#ifndef PAGE_SIZE
#define PAGE_SIZE 4096
#endif
