#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./test/ is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
"""
import os, time
from obsoleta.test.test_common import TESTDATA_PATH, execute, test_eq, title
from obsoleta.common import ErrorCode

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))


def prepare_local(master):
    execute('rm local/dixi -rf', 0, True)
    execute('mkdir -p local/dixi', 0, True)
    execute(f'cp -r {TESTDATA_PATH}/dixi/{master}/* local/dixi', 0, True)
    print(f'copy testdata from {TESTDATA_PATH}/dixi/{master} to local/dixi')


def run_dixi(args, directory='', errorcode=0):
    cmd = f'./dixi.py --conf {TESTDATA_PATH}/test.conf --path local/dixi/{directory} {args}'
    return execute(cmd, errorcode)


print('\n\n============================= dixi =============================')

title('M0', 'getname')
prepare_local('simple')
exitcode, output = run_dixi('--getname')
test_eq(output, 'a')

title('M1', 'setversion and getversion')
prepare_local('simple')
exitcode, output = run_dixi('--setversion 1.2.3')
exitcode, output = run_dixi('--getversion')
test_eq(output, '1.2.3')

title('M1B', 'setversion and getversion in depends section')
prepare_local('simple')
exitcode, output = run_dixi('--depends b --setversion 3.2.1')
exitcode, output = run_dixi('--depends b --getversion')
test_eq(output, '3.2.1')

title('M2', 'incmajor')
prepare_local('simple')
exitcode, output = run_dixi('--incmajor')
print(output)
test_eq(output, '(\'0.1.2\', \'1.1.2\')')

title('M3', 'incminor')
prepare_local('simple')
exitcode, output = run_dixi('--incminor')
test_eq(output == '(\'0.1.2\', \'0.2.2\')')

title('M4', 'incbuild')
prepare_local('simple')
exitcode, output = run_dixi('--incbuild')
test_eq(output == '(\'0.1.2\', \'0.1.3\')')

title('M5a', 'setmajor')
prepare_local('simple')
exitcode, output = run_dixi('--setmajor 99')
print(output)
test_eq(output == '(\'0.1.2\', \'99.1.2\')')

title('M5b', 'setminor')
prepare_local('simple')
exitcode, output = run_dixi('--setminor 88')
test_eq(output == '(\'0.1.2\', \'0.88.2\')')

title('M5c', 'setbuild')
prepare_local('simple')
exitcode, output = run_dixi('--setbuild 77')
test_eq(output == '(\'0.1.2\', \'0.1.77\')')

title('M6', 'getcompact')
prepare_local('simple')
exitcode, output = run_dixi('--getcompact --delimiter _')
test_eq(output, 'a_0.1.2_development_minix_debug')

title('O1', 'settrack and gettrack')
prepare_local('simple')
exitcode, output = run_dixi('--settrack discontinued')
exitcode, output = run_dixi('--gettrack')
test_eq(output, 'discontinued')

title('P1', 'setarch and getarch')
prepare_local('simple')
exitcode, output = run_dixi('--setarch beos')
exitcode, output = run_dixi('--getarch')
test_eq(output, 'beos')

title('Q1', 'setbuildtype and getbuildtype')
prepare_local('simple')
exitcode, output = run_dixi('--setbuildtype release_stripped')
exitcode, output = run_dixi('--getbuildtype')
test_eq(output, 'release_stripped')

title('Q2', 'setvalue and getvalue')
prepare_local('simple')
exitcode, output = run_dixi('--setvalue "key this is the value"')
exitcode, output = run_dixi('--getvalue key')
test_eq(output, 'this is the value')


title('R1', 'slotted setversion and getversion')
prepare_local('slotted')
exitcode, output = run_dixi('--setversion 1.2.3')
exitcode, output = run_dixi('--getversion')
test_eq(output, '1.2.3')

title('R1B', 'slotted setversion and getversion in depends section')
prepare_local('slotted')
exitcode, output = run_dixi('--depends b --setversion 1.1.1')
exitcode, output = run_dixi('--depends b --getversion')
test_eq(output, '1.1.1')
exitcode, output = run_dixi('--getversion')
test_eq(output, '0.1.2')


title('R1B', 'slotted getversion with invalid key')
prepare_local('slotted_invalid_key')
exitcode, output = run_dixi('--setversion 1.2.3', errorcode=ErrorCode.INVALID_KEY_FILE.value)
print(output)
exitcode, output = run_dixi('--getversion', errorcode=ErrorCode.INVALID_KEY_FILE.value)
print(output)

title('R2', 'slotted incmajor')
prepare_local('slotted')
exitcode, output = run_dixi('--incmajor')
test_eq('1.1.2' in output)

title('R3', 'slotted incminor')
prepare_local('slotted')
exitcode, output = run_dixi('--incminor')
test_eq('0.2.2' in output)

title('R4', 'slotted incbuild')
prepare_local('slotted')
exitcode, output = run_dixi('--incbuild')
test_eq('0.1.3' in output)

title('R5', 'slotted settrack and gettrack')
prepare_local('slotted')
exitcode, output = run_dixi('--settrack discontinued')
exitcode, output = run_dixi('--gettrack')
test_eq(output, 'discontinued')

title('R6', 'slotted with version in key section, setversion and getversion')
prepare_local('slotted_working_in_key_section')
exitcode, output = run_dixi('--setversion 1.2.3')
exitcode, output = run_dixi('--getversion')
test_eq(output, '1.2.3')

title('R7', 'slotted in key section, settrack and gettrack')
prepare_local('slotted_working_in_key_section')
exitcode, output = run_dixi('--settrack discontinued')
exitcode, output = run_dixi('--gettrack')
test_eq(output, 'discontinued')

title('R8', 'slotted in key section, setarch and getarch')
prepare_local('slotted_working_in_key_section')
exitcode, output = run_dixi('--setarch x86_128')
exitcode, output = run_dixi('--getarch')
test_eq(output, 'x86_128')

title('R9', 'slotted in key section, setbuildtype and getbuildtype')
prepare_local('slotted_working_in_key_section')
exitcode, output = run_dixi('--setbuildtype release')
exitcode, output = run_dixi('--getbuildtype')
test_eq(output, 'release')


title('S1', 'multislot setversion and getversion')
prepare_local('multislot')
exitcode, output = run_dixi('--setversion 1.2.3')
exitcode, output = run_dixi('--getversion')
test_eq(output, '1.2.3')

title('S1B', 'multislot setversion and getversion in depends section')
prepare_local('multislot')
exitcode, output = run_dixi('--depends b --keypath build_a --setversion 4.4.4')
exitcode, output = run_dixi('--depends b --keypath build_a --getversion')
test_eq(output, '4.4.4')

title('S1C', 'multislot setversion and getversion with invalid key')
prepare_local('multislot_invalid_key')
exitcode, output = run_dixi('--keypath build_a --setversion 1.2.3', errorcode=ErrorCode.INVALID_KEY_FILE.value)
exitcode, output = run_dixi('--keypath build_a --getversion', errorcode=ErrorCode.INVALID_KEY_FILE.value)

title('S1D', 'multislot get arch, buildtype and track of which none is defined, falling back to defaults')
prepare_local('multislot')
exitcode, output = run_dixi('--gettrack', errorcode=ErrorCode.OK.value)
test_eq(output, 'anytrack')
exitcode, output = run_dixi('--getarch', errorcode=ErrorCode.OK.value)
test_eq(output, 'anyarch')
exitcode, output = run_dixi('--getbuildtype', errorcode=ErrorCode.OK.value)
test_eq(output, 'unknown')

title('S1E', 'multislot setarch and getarch')
prepare_local('multislot')
exitcode, output = run_dixi('--setarch production', errorcode=ErrorCode.OK.value)
exitcode, output = run_dixi('--getarch', errorcode=ErrorCode.OK.value)
test_eq(output, 'production')

title('S2A', 'multislot get arch from build dir. Requires "relaxed_multislot" in configuration')
prepare_local('multislot')
exitcode, output = run_dixi('--getarch', 'build_x', errorcode=ErrorCode.OK.value)
test_eq(output, 'anyarch')

title('S2B', 'as above but arch from build_a folder')
prepare_local('multislot')
exitcode, output = run_dixi('--getarch', 'build_a', errorcode=ErrorCode.OK.value)
test_eq(output, 'x86_64')


title('T1', 'printtemplate')
exitcode, output = run_dixi('--printtemplate')
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
prepare_local('simple_print')
exitcode, output = run_dixi('--print')
test_eq("""{
  "name": "a",
  "version": "0.1.2",
  "track": "development",
  "arch": "minix",
  "buildtype": "debug",
  "readonly": true,
  "depends": [
    {
      "name": "b",
      "version": "0.1.3",
      "track": "development",
      "buildtype": "debug",
      "what_about_a_boolean": false,
      "arch": "minix"
    },
    {
      "name": "c",
      "version": "0.1.4",
      "track": "production",
      "buildtype": "debug",
      "bump": false,
      "arch": "minix"
    }
  ]
}""" in output)

print('test_dixi took %.3f secs' % (time.time() - start_time))

print("\npass\n")
