#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./test/ is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
In case a test fails then the program exits immediately.
"""
from common import ErrorCode
from test_common import execute, test, title
import os
import time

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(obsoleta_root)

exit_code = ErrorCode.OK

print('\n\n============================= obsoleta =============================')

fixed = './obsoleta.py --conf test.conf '

title('A1', 'first check that this test suite matches the used obsoleta')
err, output = execute(fixed + '--root test/A1_test_obsoleta:. --package testsuite --check', ErrorCode.OK)

title('A2', 'simple sunshine --tree')
err, output = execute(fixed + '--root test/A2_test_simple --package \'*\' --tree', ErrorCode.OK)
test(len(output[:-1].split('\n')), 6)

title('A3', 'simple sunshine --list')
err, output = execute(fixed + '--root test/A2_test_simple --package a --check', ErrorCode.OK)

title('A4', 'simple sunshine --buildorder')
err, output = execute(fixed + '--root test/A2_test_simple --package a --buildorder', ErrorCode.OK)
test(output == ('c:anytrack:anyarch:unknown:0.1.2\nb:anytrack:anyarch:unknown:0.1.2\na:anytrack:anyarch:unknown:0.1.2\n'))

title('A5', 'simple sunshine --buildorder --printpaths')
err, output = execute(fixed + '--root test/A2_test_simple --package a --buildorder --printpaths', ErrorCode.OK)
output = output.split('\n')
test(output[0].endswith('c'))
test(output[1].endswith('b'))
test(output[2].endswith('a'))

title('A6', 'simple sunshine --locate')
err, output = execute(fixed + '--root test/A2_test_simple --package a --locate', ErrorCode.OK)
test(output is not None)


title('B1', 'no json files found (bad path)')
err, output = execute(fixed + '--root nonexisting --package a --check', ErrorCode.BAD_PATH)

title('B2', 'json syntax error')
err, output = execute(fixed + '--root exception/B2_test_json_error --package a --check', ErrorCode.SYNTAX_ERROR)

title('B3', 'missing name')
err, output = execute(fixed + '--root exception/B3_test_missing_name --package a --check', ErrorCode.MISSING_INPUT)

title('B4', 'missing version')
err, output = execute(fixed + '--root exception/B4_test_missing_version --package a --check', ErrorCode.MISSING_INPUT)

title('B5', 'missing package')
err, output = execute(fixed + '--root test/B5_test_missing_package --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('B6', 'missing package - a:development <<< b:testing <<< c:anytrack should fail')
err, output = execute(fixed + '--root test/B6_test_missing_package_track --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('B7', 'no package found, --locate')
err, output = execute(fixed + '--root test/A2_test_simple --package found --locate', ErrorCode.PACKAGE_NOT_FOUND)
test(output == "")


title('C1', "a anyarch <<< b anyarch <<< c arch is ok")
err, output = execute(fixed + '--root test/C1_test_different_arch_dev_dev_arch1 --package a --check', ErrorCode.OK)

title('C2', "b requires a c that is missing. There is a c but its a different arch.")
err, output = execute(fixed + '--root test/C2_test_different_arch_dev_arch1_arch2 --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('C3', "different buildtypes are ok for non-production build")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --package a --tree', ErrorCode.OK)
test("b:testing:anyarch:release:0.1.2" in output)

title('C4', "different buildtypes are not ok for production build")
err, output = execute(fixed + '--root test/C4_test_different_buildtypes_production --package a --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('C5', 'failing since a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute(fixed + '--root test/C5_test_multiple_versions --package a --check', ErrorCode.MULTIPLE_VERSIONS)
print(output)
test("c:anytrack:anyarch:unknown:1.2.3" in output)
test("c:anytrack:anyarch:unknown:1.2.4" in output)

title('C6', 'testing d is ok, a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
err, output = execute(fixed + '--root test/C5_test_multiple_versions --package d --check', ErrorCode.OK)

title('C7', 'fail to list buildorder as there are a circular dependency')
err, output = execute(fixed + '--root test/C7_test_circular_dependency --package \* --buildorder', ErrorCode.CIRCULAR_DEPENDENCY)

title('C8', 'named architecture -> named architecture -> "anyarch" is ok')
err, output = execute(fixed + '--root test/C8_test_arch_noarch --package a:anytrack:beos --check', ErrorCode.OK)


title('D1', 'find b in version 0.2.0')
err, output = execute(fixed + '--root test/D1_range_find_newest --package a --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title('D2', 'find b in version 0.2.0')
err, output = execute(fixed + '--root test/D1_range_find_newest --package c --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title('D3', 'find b in version 0.2.0')
err, output = execute(fixed + '--root test/D1_range_find_newest --package d --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title('D4', 'find b in version 0.2.0')
err, output = execute(fixed + '--root test/D1_range_find_newest --package e --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.2.0" in output)

title('D5', 'find b in version 0.1.2, higher versions exist but they are discontiued and defective respectively')
err, output = execute(fixed + '--root test/D5_test_discontinued_defective --package a --tree', ErrorCode.OK)
test("b:anytrack:anyarch:unknown:0.1.2" in output)


title('E1', "testing compact 5:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --package a:development:anyarch:debug:0.1.2 --tree', ErrorCode.OK)

title('E2', "testing compact 4:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --package a:development:anyarch:debug --tree', ErrorCode.OK)

title('E3', "testing compact 3:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --package a:development:anyarch --tree', ErrorCode.OK)

title('E4', "testing compact 2:5 (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --package a:development --tree', ErrorCode.OK)

title('E5', "testing compact with package path (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --path test/C3_test_different_buildtypes/a --tree', ErrorCode.OK)

title('E6', "testing compact with package path (using different buildtypes are ok for non-production build)")
err, output = execute(fixed + '--root test/C3_test_different_buildtypes --path test/C3_test_different_buildtypes/a --tree', ErrorCode.OK)


title('F1', "duplicate package")
err, output = execute(fixed + '--root test/F1_test_duplicate_package --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title('F2', "duplicate package - slot test 1, fails since 'a' is not unique enough")
err, output = execute(fixed + '--root test/F2_test_duplicate_package_slotted_ok --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title('F3', "duplicate package - slot test 1, fails since 'a' is not unique enough")
err, output = execute(fixed + '--root test/F2_test_duplicate_package_slotted_ok --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title('F4', "duplicate package - slot test 1, pass, b in x86 found")
err, output = execute(fixed + '--root test/F2_test_duplicate_package_slotted_ok --package a:anytrack:x86 --tree', ErrorCode.OK)

title('F5', "duplicate package - slot test 1, fail, b in x86_64 not found")
err, output = execute(fixed + '--root test/F2_test_duplicate_package_slotted_ok --package a:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F6', "duplicate package - slot test 2, fail, a in x86 not found")
err, output = execute(fixed + '--root test/F3_test_duplicate_package_slotted_missing_b --package a:anytrack:x86 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F7', "duplicate package - slot test 2, fail, b in x86_64 not found")
err, output = execute(fixed + '--root test/F3_test_duplicate_package_slotted_missing_b --package a:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F8', "duplicate package - passes since there is a skip file")
err, output = execute(fixed + '--root test/F4_test_duplicate_package_with_skip_file --package a --tree', ErrorCode.OK)

title('F9', "slot - missing key file")
err, output = execute(fixed + '--root test/F5_test_slotted_missing_key_file --package a --tree', ErrorCode.MISSING_KEY_FILE)

title('F10', "slot - invalid key file")
err, output = execute(fixed + '--root test/F6_test_slotted_bad_key_file --package a --tree', ErrorCode.INVALID_KEY_FILE)

title('G1', "multislot sunshine")
err, output = execute(fixed + '--root test/G1_test_multislot --package a --tree --depth 2', ErrorCode.OK)


print('test suite took %.3f secs' % (time.time() - start_time))

print("\npass\n")
