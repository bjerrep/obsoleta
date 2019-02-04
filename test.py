#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./test/ is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
"""
from common import ErrorCode
import subprocess
import os
import time

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(obsoleta_root)

exit_code = ErrorCode.OK


def execute(command, expected_exit_code):
    global exit_code
    try:
        expected_exit_code = expected_exit_code.value
    except:
        pass

    try:
        print('testing "%s"' % command)
        output = None
        output = subprocess.check_output(command, shell=True)
        output = output.decode()
        print(output)
        if expected_exit_code != ErrorCode.OK.value:
            print('  process fail - didnt return exit code %i' % (expected_exit_code))
            exit_code = ErrorCode.TEST_FAILED
        return 0, output
    except subprocess.CalledProcessError as e:
        output = e.stdout.decode()
        if e.returncode != expected_exit_code:
            print('  process fail - unexpected exit code (not %i): %s' % (expected_exit_code, str(e)))
            exit_code = ErrorCode.TEST_FAILED
            exit(exit_code.value)
        else:
            print('  process pass with expected exit code %i %s' % (expected_exit_code, ErrorCode.to_string(expected_exit_code)))
        return e.returncode, output


def test(a, b=True):
    global exit_code
    if a != b:
        print('   assertion failed: %s != %s' % (str(a), str(b)))
        exit_code = ErrorCode.TEST_FAILED


def title(serial, purpose):
    print()
    print('---------------------------------------------')
    print('Test ' + str(serial))
    print(purpose)
    print('---------------------------------------------')


fixed = './obsoleta.py --conf test.conf '

title(1, 'first check that this test suite matches the used obsoleta')
err, output = execute(fixed + '--path test/test_obsoleta:. --package testsuite --check', ErrorCode.OK)

title(10, 'simple sunshine --tree')
err, output = execute(fixed + '--path test/test_simple --package \'*\' --tree', ErrorCode.OK)
test(len(output[:-1].split('\n')), 6)

title(11, 'simple sunshine --list')
err, output = execute(fixed + '--path test/test_simple --package a --check', ErrorCode.OK)

title(12, 'simple sunshine --buildorder')
err, output = execute(fixed + '--path test/test_simple --package a --buildorder', ErrorCode.OK)
test(output == ('c:anytrack:anyarch:unknown:0.1.2\nb:anytrack:anyarch:unknown:0.1.2\na:anytrack:anyarch:unknown:0.1.2\n'))

title(13, 'simple sunshine --buildorder --printpaths')
err, output = execute(fixed + '--path test/test_simple --package a --buildorder --printpaths', ErrorCode.OK)
test(output == ('/home/claus/src/obsoleta/test/test_simple/c\n/home/claus/src/obsoleta/test/test_simple/b\n'
                '/home/claus/src/obsoleta/test/test_simple/a\n'))

title(20, 'no json files found (bad path)')
err, output = execute(fixed + '--path nonexisting --package a --check', ErrorCode.BAD_PATH)

title(21, 'json syntax error')
err, output = execute(fixed + '--path exception/test_json_error --package a --check', ErrorCode.SYNTAX_ERROR)

title(22, 'missing name')
err, output = execute(fixed + '--path exception/test_missing_name --package a --check', ErrorCode.MISSING_INPUT)

title(23, 'missing version')
err, output = execute(fixed + '--path exception/test_missing_version --package a --check', ErrorCode.MISSING_INPUT)

title(24, 'missing package')
err, output = execute(fixed + '--path test/test_missing_package --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title(25, 'missing package - a:development <<< b:testing <<< c:anytrack should fail')
err, output = execute(fixed + '--path test/test_missing_package_track --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title(30, "a anyarch <<< b anyarch <<< c arch is ok")
err, output = execute(fixed + '--path test/test_different_arch_dev_dev_arch1 --package a --check', ErrorCode.OK)

title(31, "b requires a c that is missing. There is a c but its a different arch.")
err, output = execute(fixed + '--path test/test_different_arch_dev_arch1_arch2 --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title(32, "different buildtypes are ok for non-production build")
err, output = execute(fixed + '--path test/test_different_buildtypes --package a --tree', ErrorCode.OK)
test("b:testing:anyarch:release:0.1.2" in output)

title(33, "different buildtypes are not ok for production build")
err, output = execute(fixed + '--path test/test_different_buildtypes_production --package a --tree', ErrorCode.PACKAGE_NOT_FOUND)

title(35, 'failing since a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute(fixed + '--path test/test_multiple_versions --package a --check', ErrorCode.MULTIPLE_VERSIONS)
print(output)
test("c:anytrack:anyarch:unknown:1.2.3" in output)
test("c:anytrack:anyarch:unknown:1.2.4" in output)

title(36, 'testing d is ok, a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute(fixed + '--path test/test_multiple_versions --package d --check', ErrorCode.OK)

title(37, 'fail to list buildorder as there are a circular dependency')
err, output = execute(fixed + '--path test/test_circular_dependency --package \* --buildorder', ErrorCode.CIRCULAR_DEPENDENCY)

title(40, 'find b in version 0.2.0')
err, output = execute(fixed + '--path test/range_find_newest --package a --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(41, 'find b in version 0.2.0')
err, output = execute(fixed + '--path test/range_find_newest --package c --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(42, 'find b in version 0.2.0')
err, output = execute(fixed + '--path test/range_find_newest --package d --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(43, 'find b in version 0.2.0')
err, output = execute(fixed + '--path test/range_find_newest --package e --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(50, 'find b in version 0.1.2, higher versions exist but they are discontiued and defective respectively')
err, output = execute(fixed + '--path test/test_discontinued_defective --package a --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.1.2" in output)

title(100, "testing compact 5:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --package a:development:anyarch:debug:0.1.2 --tree', ErrorCode.OK)

title(101, "testing compact 4:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --package a:development:anyarch:debug --tree', ErrorCode.OK)

title(102, "testing compact 3:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --package a:development:anyarch --tree', ErrorCode.OK)

title(103, "testing compact 2:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --package a:development --tree', ErrorCode.OK)

title(104, "testing compact with package path (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --json test/test_different_buildtypes/a --tree', ErrorCode.OK)

title(104, "testing compact with package path (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--path test/test_different_buildtypes --json test/test_different_buildtypes/a --tree', ErrorCode.OK)

title(200, "duplicate package")
err, output = execute(fixed + '--path test/test_duplicate_package --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title(300, "duplicate package - slot test 1, fails since 'a' is not unique enough")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_ok --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title(301, "duplicate package - slot test 1, fails since 'a' is not unique enough")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_ok --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title(302, "duplicate package - slot test 1, pass, b in x86 found")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_ok --package a:anytrack:x86 --tree', ErrorCode.OK)

title(303, "duplicate package - slot test 1, fail, b in x86_64 not found")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_ok --package a:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title(400, "duplicate package - slot test 2, fail, a in x86 not found")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_missing_b --package a:anytrack:x86 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title(401, "duplicate package - slot test 2, fail, b in x86_64 not found")
err, output = execute(fixed + '--path test/test_duplicate_package_slotted_missing_b --package a:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)


print('test suite took %.3f secs' % (time.time() - start_time))

if exit_code == ErrorCode.OK:
    print("\npass\n")
else:
    print("\nfail\n")

exit(exit_code.value)
