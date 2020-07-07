#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./test/ is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
"""
from test_common import execute, test_eq, title
from common import ErrorCode
import os
import time

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(obsoleta_root)


def prepare_local(master):
    execute('rm local/dixi -rf', 0, True)
    execute('mkdir -p local/dixi', 0, True)
    execute('cp -r testdata/dixi/' + master + '/* local/dixi', 0, True)


print('\n\n============================= dixi =============================')

_fixed = './dixi.py --conf testdata/test.conf '
fixed = _fixed + ' --path local/dixi '

title('M0', 'getname')
prepare_local('simple')
exitcode, output = execute(fixed + '--getname')
test_eq(output, 'a')

title('M1', 'setversion and getversion')
prepare_local('simple')
exitcode, output = execute(fixed + '--setversion 1.2.3')
exitcode, output = execute(fixed + '--getversion')
test_eq(output, '1.2.3')

title('M1B', 'setversion and getversion in depends section')
prepare_local('simple')
exitcode, output = execute(fixed + '--depends b --setversion 3.2.1')
exitcode, output = execute(fixed + '--depends b --getversion')
test_eq(output, '3.2.1')

title('M2', 'incmajor')
prepare_local('simple')
exitcode, output = execute(fixed + '--incmajor')
print(output)
test_eq(output == '(\'0.1.2\', \'1.1.2\')')

title('M3', 'incminor')
prepare_local('simple')
exitcode, output = execute(fixed + '--incminor')
test_eq(output == '(\'0.1.2\', \'0.2.2\')')

title('M4', 'incbuild')
prepare_local('simple')
exitcode, output = execute(fixed + '--incbuild')
test_eq(output == '(\'0.1.2\', \'0.1.3\')')

title('M5a', 'setmajor')
prepare_local('simple')
exitcode, output = execute(fixed + '--setmajor 99')
print(output)
test_eq(output == '(\'0.1.2\', \'99.1.2\')')

title('M5b', 'setminor')
prepare_local('simple')
exitcode, output = execute(fixed + '--setminor 88')
test_eq(output == '(\'0.1.2\', \'0.88.2\')')

title('M5c', 'setbuild')
prepare_local('simple')
exitcode, output = execute(fixed + '--setbuild 77')
test_eq(output == '(\'0.1.2\', \'0.1.77\')')

title('M6', 'getcompact')
prepare_local('simple')
exitcode, output = execute(fixed + '--getcompact')
test_eq(output, 'a:0.1.2:testing:minix:debug')

title('O1', 'settrack and gettrack')
prepare_local('simple')
exitcode, output = execute(fixed + '--settrack discontinued')
exitcode, output = execute(fixed + '--gettrack')
test_eq(output, 'discontinued')

title('P1', 'setarch and getarch')
prepare_local('simple')
exitcode, output = execute(fixed + '--setarch beos')
exitcode, output = execute(fixed + '--getarch')
test_eq(output, 'beos')

title('Q1', 'setbuildtype and getbuildtype')
prepare_local('simple')
exitcode, output = execute(fixed + '--setbuildtype release_stripped')
exitcode, output = execute(fixed + '--getbuildtype')
test_eq(output, 'release_stripped')

title('Q2', 'setvalue and getvalue')
prepare_local('simple')
exitcode, output = execute(fixed + '--setvalue "key this is the value"')
exitcode, output = execute(fixed + '--getvalue key')
test_eq(output, 'this is the value')


title('R1', 'slotted setversion and getversion')
prepare_local('slotted')
exitcode, output = execute(fixed + '--setversion 1.2.3')
exitcode, output = execute(fixed + '--getversion')
test_eq(output, '1.2.3')

title('R1B', 'slotted setversion and getversion in depends section')
prepare_local('slotted')
exitcode, output = execute(fixed + '--depends b --setversion 1.1.1')
exitcode, output = execute(fixed + '--depends b --getversion')
test_eq(output, '1.1.1')

title('R1B', 'slotted getversion with invalid key')
prepare_local('slotted_invalid_key')
exitcode, output = execute(fixed + '--setversion 1.2.3', ErrorCode.INVALID_KEY_FILE.value)
print(output)
exitcode, output = execute(fixed + '--getversion', ErrorCode.INVALID_KEY_FILE.value)
print(output)

title('R2', 'slotted incmajor')
prepare_local('slotted')
exitcode, output = execute(fixed + '--incmajor')
test_eq('1.1.2' in output)

title('R3', 'slotted incminor')
prepare_local('slotted')
exitcode, output = execute(fixed + '--incminor')
test_eq('0.2.2' in output)

title('R4', 'slotted incbuild')
prepare_local('slotted')
exitcode, output = execute(fixed + '--incbuild')
test_eq('0.1.3' in output)

title('R5', 'slotted settrack and gettrack')
prepare_local('slotted')
exitcode, output = execute(fixed + '--settrack discontinued')
exitcode, output = execute(fixed + '--gettrack')
test_eq(output, 'discontinued')

title('R6', 'slotted with version in key section, setversion and getversion')
prepare_local('slotted_working_in_key_section')
exitcode, output = execute(fixed + '--setversion 1.2.3')
exitcode, output = execute(fixed + '--getversion')
test_eq(output, '1.2.3')

title('R7', 'slotted in key section, settrack and gettrack')
prepare_local('slotted_working_in_key_section')
exitcode, output = execute(fixed + '--settrack discontinued')
exitcode, output = execute(fixed + '--gettrack')
test_eq(output, 'discontinued')

title('R8', 'slotted in key section, setarch and getarch')
prepare_local('slotted_working_in_key_section')
exitcode, output = execute(fixed + '--setarch x86_128')
exitcode, output = execute(fixed + '--getarch')
test_eq(output, 'x86_128')

title('R9', 'slotted in key section, setbuildtype and getbuildtype')
prepare_local('slotted_working_in_key_section')
exitcode, output = execute(fixed + '--setbuildtype release')
exitcode, output = execute(fixed + '--getbuildtype')
test_eq(output, 'release')


title('S1', 'multislot setversion and getversion')
prepare_local('multislot')
exitcode, output = execute(fixed + '--keypath build_a --setversion 1.2.3')
exitcode, output = execute(fixed + '--keypath build_a --getversion')
test_eq(output, '1.2.3')

title('S1B', 'multislot setversion and getversion in depends section')
prepare_local('multislot')
exitcode, output = execute(fixed + '--depends b --keypath build_a --setversion 4.4.4')
exitcode, output = execute(fixed + '--depends b --keypath build_a --getversion')
test_eq(output, '4.4.4')

title('S1C', 'multislot setversion and getversion with invalid key')
prepare_local('multislot_invalid_key')
exitcode, output = execute(fixed + '--keypath build_a --setversion 1.2.3', ErrorCode.INVALID_KEY_FILE.value)
exitcode, output = execute(fixed + '--keypath build_a --getversion', ErrorCode.INVALID_KEY_FILE.value)

title('S1D', 'multislot get arch, buildtype and track of which none is defined, falling back to defaults')
prepare_local('multislot')
exitcode, output = execute(fixed + '--keypath build_x --gettrack', ErrorCode.OK.value)
test_eq(output, 'anytrack')
exitcode, output = execute(fixed + '--keypath build_x --getarch', ErrorCode.OK.value)
test_eq(output, 'anyarch')
exitcode, output = execute(fixed + '--keypath build_x --getbuildtype', ErrorCode.OK.value)
test_eq(output, 'unknown')

title('S1E', 'multislot get arch from build dir. Requires "relaxed_multislot" in setup')
prepare_local('multislot')
exitcode, output = execute(_fixed + '--path local/dixi/build_x --gettrack', ErrorCode.OK.value)
test_eq(output, 'anytrack')


title('T1', 'printtemplate')
exitcode, output = execute(fixed + '--printtemplate')
test_eq('''{
  "name": "a",
  "version": "0.0.0",
  "track": "development",
  "arch": "archname",
  "buildtype": "buildtype",
  "depends": [
    {
      "name": "b",
      "version": "0.0.0",
      "track": "development",
      "arch": "archname",
      "buildtype": "buildtype"
    }
  ]
}''' in output)


title('T2', 'print')
prepare_local('multislot')
exitcode, output = execute(fixed + '--keypath build_a --print')
test_eq("""{
  "name": "a",
  "version": "0.1.2",
  "arch": "x86_64",
  "depends": [
    {
      "name": "b",
      "version": "0.1.2",
      "arch": "x86_64"
    }
  ]
}""" in output)

print('test suite took %.3f secs' % (time.time() - start_time))

print("\npass\n")
