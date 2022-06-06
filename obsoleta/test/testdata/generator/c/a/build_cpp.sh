#!/bin/bash
set -e

g++ -o a_cpp -Iinc -I../b/inc src/obsoleta.c src/obsoleta_a.c src/obsoleta_a_cpp.cpp src/main.cpp -L../b -lb_shared
