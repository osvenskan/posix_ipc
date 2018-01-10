#!/usr/bin/env bash

# Linker opts should be blank for OS X, FreeBSD and OpenSolaris
#LINKER_OPTIONS=""

# On Linux, we must link with realtime and thread libraries
LINKER_OPTIONS="-lrt -lpthread"

gcc -Wall -c -o md5.o md5.c
gcc -Wall -c -o utils.o utils.c
gcc -Wall md5.o utils.o -o premise premise.c -L. $LINKER_OPTIONS
gcc -Wall md5.o utils.o -o conclusion conclusion.c -L. $LINKER_OPTIONS
