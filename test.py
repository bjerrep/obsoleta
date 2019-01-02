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

obsoleta_root = os.path.dirname(__file__)
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


title(10, 'simple sunshine --tree')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_simple --tree all', ErrorCode.OK)
test(len(output[:-1].split('\n')), 6)

title(11, 'simple sunshine --list')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_simple --check a', ErrorCode.OK)

title(12, 'simple sunshine --buildorder')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_simple --buildorder a', ErrorCode.OK)
test(output == ('c:anytrack:anyarch:unknown:0.1.2\nb:anytrack:anyarch:unknown:0.1.2\na:anytrack:anyarch:unknown:0.1.2\n'))

title(20, 'no json files found (bad path)')
err, output = execute('./obsoleta.py --conf test.conf --path nonexisting --check a', ErrorCode.BAD_PATH)

title(21, 'json syntax error')
err, output = execute('./obsoleta.py --conf test.conf --path exception/test_json_error --check a', ErrorCode.SYNTAX_ERROR)

title(22, 'missing name')
err, output = execute('./obsoleta.py --conf test.conf --path exception/test_missing_name --check a', ErrorCode.MISSING_INPUT)

title(23, 'missing version')
err, output = execute('./obsoleta.py --conf test.conf --path exception/test_missing_version --check a', ErrorCode.MISSING_INPUT)

title(24, 'missing package')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_missing_package --check a', ErrorCode.PACKAGE_NOT_FOUND)

title(30, "a anyarch <<< b anyarch <<< c arch is ok")
err, output = execute('./obsoleta.py --conf test.conf --path test/test_different_arch_dev_dev_arch1 --check a', ErrorCode.OK)

title(31, "b requires a c that is missing. There is a c but its a different arch.")
err, output = execute('./obsoleta.py --conf test.conf --path test/test_different_arch_dev_arch1_arch2 --check a', ErrorCode.PACKAGE_NOT_FOUND)

title(32, "different buildtypes are ok for non-production build")
err, output = execute('./obsoleta.py --conf test.conf --tree a --path test/test_different_buildtypes', ErrorCode.OK)
test("b:testing:anyarch:release:0.1.2" in output)

title(33, "different buildtypes are not ok for production build")
err, output = execute('./obsoleta.py --conf test.conf --tree a --path test/test_different_buildtypes_production', ErrorCode.PACKAGE_NOT_FOUND)

title(35, 'failing since a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_multiple_versions --check a', ErrorCode.MULTIPLE_VERSIONS)
print(output)
test("c:anytrack:anyarch:unknown:1.2.3" in output)
test("c:anytrack:anyarch:unknown:1.2.4" in output)

title(36, 'testing d is ok, a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute('./obsoleta.py --conf test.conf --path test/test_multiple_versions --check d', ErrorCode.OK)

title(37, 'fail to list buildorder as there are a circular dependency')
err, output = execute('./obsoleta.py --conf test.conf --buildorder all --path test/test_circular_dependency', ErrorCode.CIRCULAR_DEPENDENCY)

title(40, 'find b in version 0.2.0')
err, output = execute('./obsoleta.py --conf test.conf --tree a --path test/range_find_newest', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(41, 'find b in version 0.2.0')
err, output = execute('./obsoleta.py --conf test.conf --tree c --path test/range_find_newest', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(42, 'find b in version 0.2.0')
err, output = execute('./obsoleta.py --conf test.conf --tree d --path test/range_find_newest', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(43, 'find b in version 0.2.0')
err, output = execute('./obsoleta.py --conf test.conf --tree e --path test/range_find_newest', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title(50, 'find b in version 0.1.2, higher versions exist but they are discontiued and defective respectively')
err, output = execute('./obsoleta.py --conf test.conf --tree a --path test/test_discontinued_defective', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.1.2" in output)

print('test suite took %.3f secs' % (time.time() - start_time))

if exit_code == ErrorCode.OK:
    print("\npass\n")
else:
    print("\nfail\n")

exit(exit_code.value)
