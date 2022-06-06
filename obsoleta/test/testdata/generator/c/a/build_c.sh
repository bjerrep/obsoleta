#!/bin/bash
set -e

gcc -o a_c -Iinc -I../b/inc src/obsoleta.c src/obsoleta_a.c src/main.c -L../b -lb_shared
