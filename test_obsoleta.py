#!/usr/bin/env python3
"""
Black-box test suite. Initially it seemed like a good idea to write a test suite like this,
now it is most of all annoying that this makes it impossible to debug obsoleta using the test directly...
./testdata is tests that executes without fatal problems and ./exception/ is for tests that makes Obsoleta give up.
In case a test fails then the program exits immediately.

Tests that need to modify the testdata should use populate_local_temp() to get a temporary copy to work on.
"""
# flake8: noqa E502
from errorcodes import ErrorCode
from test_common import execute, test_eq, test_ok, title, populate_local_temp
import os
import time

start_time = time.time()

obsoleta_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(obsoleta_root)

exit_code = ErrorCode.OK

print('\n\n============================= obsoleta =============================')

fixed = './obsoleta.py --conf testdata/test.conf '

title('A1', 'first check that this test suite matches the used obsoleta')
exitcode, output = execute(fixed + '--root testdata/A1_test_obsoleta:.. --depth 1 --package testsuite --check', ErrorCode.OK)

title('A2', 'simple sunshine --tree')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package \'*\' --tree --info', ErrorCode.OK)
print(output)
test_pass = """a:0.1.2:anytrack:anyarch:unknown
  b:1.1.2:anytrack:linux_x86_64:unknown
    d:0.1.2:anytrack:linux_x86_64:release
    c:2.1.2:anytrack:anyarch:unknown
      e:1.2.3:anytrack:linux_x86_64:unknown
d:0.1.2:anytrack:linux_x86_64:release
b:1.1.2:anytrack:linux_x86_64:unknown
  d:0.1.2:anytrack:linux_x86_64:release
  c:2.1.2:anytrack:anyarch:unknown
    e:1.2.3:anytrack:linux_x86_64:unknown
e:1.2.3:anytrack:linux_x86_64:unknown
c:2.1.2:anytrack:anyarch:unknown
  e:1.2.3:anytrack:linux_x86_64:unknown""" in output
test_eq(test_pass)

title('A3', 'simple sunshine --check')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package a --check', ErrorCode.OK)

title('A4', 'simple sunshine --buildorder')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package a --buildorder', ErrorCode.OK)
test_eq("""d:0.1.2:anytrack:linux_x86_64:release
e:1.2.3:anytrack:linux_x86_64:unknown
c:2.1.2:anytrack:anyarch:unknown
b:1.1.2:anytrack:linux_x86_64:unknown
a:0.1.2:anytrack:anyarch:unknown""" in output)

title('A5', 'simple sunshine --buildorder --printpaths')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package a --buildorder --printpaths', ErrorCode.OK)
output = output.split('\n')
test_eq(output[0].endswith('d'))
test_eq(output[1].endswith('e'))
test_eq(output[2].endswith('c'))
test_eq(output[3].endswith('b'))
test_eq(output[4].endswith('a'))

title('A6', 'simple sunshine --upstream')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package a --upstream', ErrorCode.OK)
test_eq(output is not None)

title('A7', 'simple sunshine --buildorder a::anytrack')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package a::anytrack --buildorder', ErrorCode.OK)
print(output)
test_eq("""d:0.1.2:anytrack:linux_x86_64:release
e:1.2.3:anytrack:linux_x86_64:unknown
c:2.1.2:anytrack:anyarch:unknown
b:1.1.2:anytrack:linux_x86_64:unknown
a:0.1.2:anytrack:anyarch:unknown""" in output)

title('A8', 'finding upstreams to "a" failing due to json error in unused "c"')
exitcode, output = execute(fixed + '--root testdata/A3_test_simple_bad_json --package a --upstream', ErrorCode.BAD_PACKAGE_FILE)
test_eq('A3_test_simple_bad_json/c/obsoleta.json' in output)

title('A9', 'as A8 but succeeds due to --keepgoing argument')
exitcode, output = execute(fixed + '--root testdata/A3_test_simple_bad_json --package a --upstream --keepgoing', ErrorCode.OK)
test_eq('A3_test_simple_bad_json/b' in output)

title('A10', 'simple sunshine --listmissing "*"')
exitcode, output = execute(fixed + '--root testdata/E1_list_missing_packages --package "*" --listmissing', ErrorCode.OK)
test_eq("""b:1.1.1:anytrack:c64:unknown
e:1.1.1:anytrack:c64:unknown
y:1.1.1:anytrack:vic20:unknown""" in output)

title('A11', 'simple sunshine --listmissing a')
exitcode, output = execute(fixed + '--root testdata/E1_list_missing_packages --package a --listmissing', ErrorCode.OK)
test_eq("""b:1.1.1:anytrack:c64:unknown
e:1.1.1:anytrack:c64:unknown""" in output)


title('B1', 'no json files found (bad path)')
exitcode, output = execute(fixed + '--root nonexisting --package a --check', ErrorCode.BAD_PATH)

title('B2', 'json syntax error')
exitcode, output = execute(fixed + '--root ./exception/B2_test_json_error --package a --check', ErrorCode.BAD_PACKAGE_FILE)

title('B3', 'missing name')
exitcode, output = execute(fixed + '--root ./exception/B3_test_missing_name --package a --check', ErrorCode.BAD_PACKAGE_FILE)

title('B4', 'missing version')
exitcode, output = execute(fixed + '--root ./exception/B4_test_missing_version --package a --check', ErrorCode.BAD_PACKAGE_FILE)

title('B5', 'missing package --check')
exitcode, output = execute(fixed + '--root testdata/B5_test_missing_package --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('B6', 'missing package --buildorder')
exitcode, output = execute(fixed + '--root testdata/B5_test_missing_package --package a --buildorder', ErrorCode.PACKAGE_NOT_FOUND)

title('B7', 'missing package --buildorder --printpaths')
exitcode, output = execute(fixed + '--root testdata/B5_test_missing_package --package a --buildorder --printpaths', ErrorCode.PACKAGE_NOT_FOUND)

title('B8', 'missing package - a:development <<< b:testing <<< c:anytrack should fail')
exitcode, output = execute(fixed + '--root testdata/B6_test_missing_package_track --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('B9', 'no package found, --upstream')
exitcode, output = execute(fixed + '--root testdata/A2_test_simple --package found --upstream', ErrorCode.PACKAGE_NOT_FOUND)
test_eq("unable to locate upstream found:*:anytrack:anyarch:unknown" in output)

title('B10', 'no package found, --listmissing z')
exitcode, output = execute(fixed + '--root testdata/E1_list_missing_packages --package z --listmissing', ErrorCode.PACKAGE_NOT_FOUND)


title('C1', "a anyarch <<< b anyarch <<< c arch is ok")
exitcode, output = execute(fixed + '--root testdata/C1_test_different_arch_dev_dev_arch1 --package a --check', ErrorCode.OK)

title('C2', "b requires a c that is missing. There is a c but its a different arch.")
exitcode, output = execute(fixed + '--root testdata/C2_test_different_arch_dev_arch1_arch2 --package a --check', ErrorCode.PACKAGE_NOT_FOUND)

title('C3', "different buildtypes are ok for non-production build")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --package a --tree', ErrorCode.OK)
test_eq("b:0.1.2:testing:anyarch:release" in output)

title('C4', "different buildtypes are not ok for production build")
exitcode, output = execute(fixed + '--root testdata/C4_test_different_buildtypes_production --package a --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('C5', 'failing since a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
exitcode, output = execute(fixed + '--root testdata/C5_test_multiple_versions --package a --check', ErrorCode.MULTIPLE_VERSIONS)
print(output)
test_eq("c:1.2.3:anytrack:anyarch:unknown" in output)
test_eq("c:1.2.3:anytrack:anyarch:unknown" in output)

title('C6', 'testing d is ok, a <<< c-1.2.4 but a <<< b <<< c-1.2.3 and b <<< d <<< c-1.2.4')
exitcode, output = execute(fixed + '--root testdata/C5_test_multiple_versions --package d --check', ErrorCode.OK)

title('C7', 'fail to list buildorder as there are a circular dependency')
exitcode, output = execute(fixed + '--root testdata/C7_test_circular_dependency --package a --buildorder', ErrorCode.CIRCULAR_DEPENDENCY)

title('C8', 'named architecture -> named architecture -> "anyarch" is ok')
exitcode, output = execute(fixed + '--root testdata/C8_test_arch_noarch --package a:*:anytrack:beos --check', ErrorCode.OK)

title('C9a', 'two upstream with different arch')
exitcode, output = execute(fixed + '--root testdata/C9_upstream_collisions/ --package a --tree', ErrorCode.ARCH_MISMATCH)

title('C9b', 'production upstream pulled in development downstream, thats fine')
exitcode, output = execute(fixed + '--root testdata/C9_upstream_collisions/ --package b --tree', ErrorCode.OK)

title('C9c', 'a production upstream and a development upstream is ok if downstream isn\'t production')
exitcode, output = execute(fixed + '--root testdata/C9_upstream_collisions/ --package c --tree', ErrorCode.OK)


title('D1', 'find b in version 0.2.0')
exitcode, output = execute(fixed + '--root testdata/D1_range_find_newest --package a --tree', ErrorCode.OK)
test_eq("b:0.2.0:anytrack:anyarch:unknown" in output)

title('D2', 'find b in version 0.2.0')
exitcode, output = execute(fixed + '--root testdata/D1_range_find_newest --package c --tree', ErrorCode.OK)
test_eq("b:0.2.0:anytrack:anyarch:unknown" in output)

title('D3', 'find b in version 0.2.0')
exitcode, output = execute(fixed + '--root testdata/D1_range_find_newest --package d --tree', ErrorCode.OK)
test_eq("b:0.2.0:anytrack:anyarch:unknown" in output)

title('D4', 'find b in version 0.2.0')
exitcode, output = execute(fixed + '--root testdata/D1_range_find_newest --package e --tree', ErrorCode.OK)
test_eq("b:0.2.0:anytrack:anyarch:unknown" in output)

title('D5', 'find b in version 0.1.2, higher versions exist but they are discontiued and defective respectively')
exitcode, output = execute(fixed + '--root testdata/D5_test_discontinued_defective --package a --tree', ErrorCode.OK)
test_eq("b:0.1.2:anytrack:anyarch:unknown" in output)


title('E1', "testing compact 5:5 (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --package a:0.1.2:development:anyarch:debug --tree', ErrorCode.OK)

title('E2', "testing compact 4:5 (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --package a:*:development:anyarch:debug --tree', ErrorCode.OK)

title('E3', "testing compact 3:5 (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --package a:*:development:anyarch --tree', ErrorCode.OK)

title('E4', "testing compact 2:5 (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --package a:*:development --tree', ErrorCode.OK)

title('E5', "testing compact with package path (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --path testdata/C3_test_different_buildtypes/a --tree', ErrorCode.OK)

title('E6', "testing compact with package path (using different buildtypes are ok for non-production build)")
exitcode, output = execute(fixed + '--root testdata/C3_test_different_buildtypes --path testdata/C3_test_different_buildtypes/a --tree', ErrorCode.OK)


title('F1', "duplicate package")
exitcode, output = execute(fixed + '--root testdata/F1_test_duplicate_package --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title('F2', "duplicate package - slot test 1, fails since 'a' is not unique")
exitcode, output = execute(fixed + '--root testdata/F2_test_duplicate_package_slotted_ok --package a --tree', ErrorCode.PACKAGE_NOT_UNIQUE)

title('F4', "duplicate package - slot test 1, pass since 'a:*:development:x86' is unique")
exitcode, output = execute(fixed + '--root testdata/F2_test_duplicate_package_slotted_ok --package a:*:development:x86 --tree', ErrorCode.OK)

title('F5', "duplicate package - slot test 1, fail, a in x86_64 not found")
exitcode, output = execute(fixed + '--root testdata/F2_test_duplicate_package_slotted_ok --package a:*:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F6', "duplicate package - slot test 2, fail, a in x86 not found")
exitcode, output = execute(fixed + '--root testdata/F3_test_duplicate_package_slotted_missing_b --package a:*:anytrack:x86 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F7', "duplicate package - slot test 2, fail, b in x86_64 not found")
exitcode, output = execute(fixed + '--root testdata/F3_test_duplicate_package_slotted_missing_b --package a:*:anytrack:x86_64 --tree', ErrorCode.PACKAGE_NOT_FOUND)

title('F8', "duplicate package - passes since there is a skip file")
exitcode, output = execute(fixed + '--root testdata/F4_test_duplicate_package_with_skip_file --package a --tree', ErrorCode.OK)

title('F9', "slot - missing key file")
exitcode, output = execute(fixed + '--root testdata/F5_test_slotted_missing_key_file --package a --tree', ErrorCode.MISSING_KEY_FILE)

title('F10', "slot - invalid key file")
exitcode, output = execute(fixed + '--root testdata/F6_test_slotted_bad_key_file --package a --tree', ErrorCode.INVALID_KEY_FILE)

title('F11', "duplicate package - one path is in blacklist_paths in configuration file")
exitcode, output = execute(fixed + '--root testdata/F7_test_duplicate_package_blacklist_paths --package a --tree', ErrorCode.OK)

title('F12', "duplicate package - using blacklist_paths on command line")
exitcode, output = execute(fixed + '--root testdata/F8_test_duplicate_package_blacklist_paths_command_line '
                              '--blacklist_path F8_test_duplicate_package_blacklist_paths_command_line/a2 '
                              '--package a --tree', ErrorCode.OK)


title('G1', "multislot sunshine")
exitcode, output = execute(fixed + '--root testdata/G1_test_multislot --package a --tree --depth 2', ErrorCode.OK)

title('G2a', "slot sunshine. nix arch brings in new dependency")
execute('./dixi.py --printkey key:nix > testdata/G2_test_slot/a/obsoleta.key')
exitcode, output = execute(fixed + '--root testdata/G2_test_slot --path testdata/G2_test_slot/a --package a --tree --depth 2', ErrorCode.OK)
test_eq("""a:1.1.1:anytrack:linux:unknown
  b:2.2.2:anytrack:anyarch:unknown
  c:3.3.3:anytrack:anyarch:unknown
  d:4.4.4:anytrack:linux:unknown
  e:5.5.5:anytrack:linux:unknown
    f:6.6.6:anytrack:linux:unknown""" in output)

title('G2b', "slot sunshine. win arch brings no new dependency")
root = populate_local_temp('testdata/G2_test_slot')
execute('./dixi.py --printkey key:win > %s/a/obsoleta.key' % root)
exitcode, output = execute(fixed + '--root %s --path %s/a --package a --tree --depth 2' % (root, root), ErrorCode.OK)
test_eq("""a:1.1.1:anytrack:windows:unknown
  b:2.2.2:anytrack:anyarch:unknown""" in output)

title('G3', "duplicates in depends")
exitcode, output = execute(fixed + '--root testdata/G3_duplicates_in_depends --package a --tree', ErrorCode.DUPLICATE_PACKAGE)

title('G5', "track degradation")
exitcode, output = execute(fixed + '--root testdata/G5_test_multislot_track_degradation --package a --check', ErrorCode.ILLEGAL_DEPENDENCY)

title('H1', "optionals - all enabled, upstream compact name 'c:1.2.3' is ok")
exitcode, output = execute(fixed + '--root testdata/C5_test_multiple_versions/ --upstream --package c:1.2.3', ErrorCode.OK)

title('H2', "optionals - all enabled, upstream compact name 'c:1.2.3:::' works")
exitcode, output = execute(fixed + '--root testdata/C5_test_multiple_versions/ --upstream --package c:1.2.3:::', ErrorCode.OK)

title('H3', "optionals - none enabled, upstream compact name 'c:1.2.3' works")
exitcode, output = execute('./obsoleta.py --conf testdata/test_no_optionals.conf --root testdata/C5_test_multiple_versions/ --upstream --package c:1.2.3', ErrorCode.OK)

title('H4', "optionals - none enabled, upstream compact name 'c::::1.2.3' fails")
exitcode, output = execute('./obsoleta.py --conf testdata/test_no_optionals.conf --root testdata/C5_test_multiple_versions/ --upstream --package c::::1.2.3', ErrorCode.COMPACT_PARSE_ERROR)

title('I1', "optionals - all enabled, upstream compact name 'c:1.2.3' finds b")
errorcode, output = execute(fixed + '--root testdata/C5_test_multiple_versions/ --downstream --package c:1.2.3', ErrorCode.OK)
test_eq("C5_test_multiple_versions/b" in output)

title('J1', "bump a downstream package")
root = populate_local_temp('testdata/G2_test_slot')
exitcode, output = execute(fixed + '--root %s --bump --package a --version 7.9.13' % root, ErrorCode.OK)
print(output)
test_eq("""bumped upstream {a:1.1.1:anytrack:linux:unknown} from 1.1.1 to 7.9.13 in "a"
no {a:1.1.1:anytrack:linux:unknown} downstream packages found""" in output)
exitcode, output = execute(fixed + '--root %s --package a --check' % root, ErrorCode.OK)

title('J1b', "bump d from slot")
root = populate_local_temp('testdata/G2_test_slot')
exitcode, output = execute(fixed + '--root %s --bump --package d --version 7.9.13 --verbose' % root, ErrorCode.OK)
print(output)
test_eq("""bumped upstream {d:4.4.4:anytrack:linux:unknown} from 4.4.4 to 7.9.13 in "d"
bumped downstream {d:4.4.4:anytrack:linux:unknown} from 4.4.4 to 7.9.13 in "a\"""" in output)
exitcode, output = execute(fixed + '--root %s --package a --check' % root, ErrorCode.OK)

title('J2', "bump b from slot (bump example in readme)")
root = populate_local_temp('testdata/F2_test_duplicate_package_slotted_ok')
exitcode, output = execute(fixed + '--root %s --bump --package b:::x86 --version 7.9.13' % root, ErrorCode.OK)
print(output)
test_eq("""bumped upstream {b:2.1.2:development:x86:unknown} from 2.1.2 to 7.9.13 in "b"
bumped downstream {b:2.1.2:development:x86:debug} from 2.1.2 to 7.9.13 in "a2\"""" in output)
exitcode, output = execute(fixed + '--root %s --package a::development:x86 --check' % root, ErrorCode.OK)

title('K1', 'simple sunshine with external lib dependency --check')
exitcode, output = execute(fixed + '--root testdata/K1_system_lib_dependency --package k1 --check', ErrorCode.OK)


print('test suite took %.3f secs' % (time.time() - start_time))

print("\npass\n")
