#!/bin/bash
set -e

gcc -Iinc -I../c/inc -c -fpic src/obsoleta.c src/obsoleta_b.c src/b.c
gcc -shared -o libb_shared.so obsoleta.o obsoleta_b.o b.o ../c/libc_static.a
