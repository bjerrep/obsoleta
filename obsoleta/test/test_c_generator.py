#!/usr/bin/env python3
import os
from obsoleta.test.pyscript import dir_copy_rewrite, run, dir_construct
from obsoleta.test.test_common import test_eq, title

title('Gen-C', 'test generator c')

# copy the sources (which includes an obsoleta.json package file) and let obsoleta figure out an build order
dir_copy_rewrite('obsoleta/test/testdata/generator/c/', 'local/temp')

exitcode, paths = run(
    './obsoleta.py --conf obsoleta/test/testdata/test.conf --root local/temp --buildorder --printpaths --package a')

# and for each package dir patch the sources and run the build script
for path in paths:
    src_path = os.path.join(path, 'src')
    dir_construct(src_path)
    inc_path = os.path.join(path, 'inc')
    dir_construct(inc_path)
    generator_cmd = f'python ./obsoleta/generator.py {path} {src_path} {inc_path}'
    print(generator_cmd)
    run(generator_cmd, autoexit=True)
    run('./build_c.sh', path, autoexit=True)

# run the C executable in a and return its exitcode based on a recursive version check throughout the packages
exitcode, _ = run('LD_LIBRARY_PATH=../b/ ./a_c', paths[-1])

test_eq(exitcode == 0)


# C++
for path in paths:
    run('./build_cpp.sh', path, autoexit=True)

exitcode, _ = run('LD_LIBRARY_PATH=../b/ ./a_cpp', paths[-1])

test_eq(exitcode == 0)
