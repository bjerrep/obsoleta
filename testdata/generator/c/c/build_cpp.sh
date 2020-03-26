#!/bin/bash
set -e

gcc -Iinc -c -fpic src/obsoleta.c src/obsoleta_c.c
ar rcs libc_static.a obsoleta.o obsoleta_c.o
