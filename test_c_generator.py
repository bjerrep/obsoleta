#!/usr/bin/env python3
import pyscript, os
from test_common import test_eq, title

title('Gen-C', 'test generator c')

# copy the sources (which includes an obsoleta.json package file) and let obsoleta figure out an build order
pyscript.dir_copy_rewrite('testdata/generator/c/', 'local/temp')
exitcode, paths = pyscript.run('./obsoleta.py --conf testdata/test.conf --root local/temp --buildorder --printpaths --package a')

# and for each package dir patch the sources and run the build script
for path in paths:
    src_path = os.path.join(path, 'src')
    pyscript.dir_construct(src_path)
    inc_path = os.path.join(path, 'inc')
    pyscript.dir_construct(inc_path)
    pyscript.run('python ./generator.py %s %s %s' % (path, src_path, inc_path), autoexit=True)
    pyscript.run('./build_c.sh', path, autoexit=True)

# run the C executable in a and return its exitcode based on a recursive version check throughout the packages
exitcode, _ = pyscript.run('LD_LIBRARY_PATH=../b/ ./a_c', path)

test_eq(exitcode == 0)


# C++
for path in paths:
    pyscript.run('./build_cpp.sh', path, autoexit=True)

exitcode, _ = pyscript.run('LD_LIBRARY_PATH=../b/ ./a_cpp', path)

test_eq(exitcode == 0)
