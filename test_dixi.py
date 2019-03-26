#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./test/ is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
"""
from test_common import execute, test, title
import os
import time

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(obsoleta_root)


def prepare_local(master):
    execute('rm local/dixi -rf', 0, True)
    execute('mkdir -p local/dixi', 0, True)
    execute('cp -r test/dixi/' + master + '/* local/dixi', 0, True)


print('\n\n============================= dixi =============================')

fixed = './dixi.py --conf test.conf --path local/dixi '

title('M1', 'setversion and getversion')
prepare_local('simple')
err, output = execute(fixed + '--setversion 1.2.3')
err, output = execute(fixed + '--getversion')
test(output, '1.2.3')

title('M2', 'incmajor')
prepare_local('simple')
err, output = execute(fixed + '--incmajor')
test(output, '1.1.2')

title('M3', 'incminor')
prepare_local('simple')
err, output = execute(fixed + '--incminor')
test(output, '0.2.2')

title('M4', 'incbuild')
prepare_local('simple')
err, output = execute(fixed + '--incbuild')
test(output, '0.1.3')

title('O1', 'settrack and gettrack')
prepare_local('simple')
err, output = execute(fixed + '--settrack discontinued')
err, output = execute(fixed + '--gettrack')
test(output, 'discontinued')

title('P1', 'setarch and getarch')
prepare_local('simple')
err, output = execute(fixed + '--setarch beos')
err, output = execute(fixed + '--getarch')
test(output, 'beos')

title('Q1', 'setbuildtype and getbuildtype')
prepare_local('simple')
err, output = execute(fixed + '--setbuildtype release_stripped')
err, output = execute(fixed + '--getbuildtype')
test(output, 'release_stripped')

title('R1', 'slotted setversion and getversion')
prepare_local('slotted')
err, output = execute(fixed + '--setversion 1.2.3')
err, output = execute(fixed + '--getversion')
test(output, '1.2.3')

title('R2', 'slotted incmajor')
prepare_local('slotted')
err, output = execute(fixed + '--incmajor')
test(output, '1.1.2')

title('R3', 'slotted incminor')
prepare_local('slotted')
err, output = execute(fixed + '--incminor')
test(output, '0.2.2')

title('R4', 'slotted incbuild')
prepare_local('slotted')
err, output = execute(fixed + '--incbuild')
test(output, '0.1.3')

title('R5', 'slotted settrack and gettrack')
prepare_local('slotted')
err, output = execute(fixed + '--settrack discontinued')
err, output = execute(fixed + '--gettrack')
test(output, 'discontinued')

title('S1', 'multislot setversion and getversion')
prepare_local('multislot')
err, output = execute(fixed + '--keypath build_a --setversion 1.2.3')
err, output = execute(fixed + '--keypath build_a --getversion')
test(output, '1.2.3')


print('test suite took %.3f secs' % (time.time() - start_time))

print("\npass\n")
