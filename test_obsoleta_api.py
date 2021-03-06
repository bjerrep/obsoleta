#!/usr/bin/env python3
from test_common import title, test_true, test_ok, test_eq, test_error, populate_local_temp
from common import Position, Setup
from obsoleta_api import Args, ObsoletaApi
from obsoletacore import DownstreamFilter
from errorcodes import ErrorCode
from version import Version
from log import logger
from package import Package
import logging, os

logger.setLevel(logging.INFO)

populate_local_temp('testdata/G2_test_slot')

args = Args()
args.set_depth(2)
args.set_root('local/temp')
setup = Setup('testdata/test.conf')

obsoleta = ObsoletaApi(setup, args)

# check

title('TOA 1A', 'check')
package = Package.construct_from_compact(setup, 'a')
error, messages = obsoleta.check(package)
test_ok(error)

title('TOA 1B', 'check')
error, messages = obsoleta.check('e')
test_ok(error)

# tree

title('TOA 2A', 'tree for "a" in G2_test_slot')
error, messages = obsoleta.tree('a')
test_ok(error, messages)
test_eq(messages, [
    'a:1.1.1:anytrack:linux:unknown',
    '  b:2.2.2:anytrack:anyarch:unknown',
    '  c:3.3.3:anytrack:anyarch:unknown',
    '  d:4.4.4:anytrack:linux:unknown',
    '  e:5.5.5:anytrack:linux:unknown',
    '    f:6.6.6:anytrack:linux:unknown'])

title('TOA 2B', 'tree')
package = Package.construct_from_compact(setup, 'a')
error, messages = obsoleta.tree(package)
test_ok(error, messages)

title('TOA 2C', 'tree')
error, messages = obsoleta.tree('oups')
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

# buildorder

title('TOA 3A', 'buildorder')
error, messages = obsoleta.buildorder('a')
test_ok(error)
test_eq(str(messages),
        '[b:2.2.2:anytrack:anyarch:unknown, c:3.3.3:anytrack:anyarch:unknown, '
        'd:4.4.4:anytrack:linux:unknown, f:6.6.6:anytrack:linux:unknown, '
        'e:5.5.5:anytrack:linux:unknown, a:1.1.1:anytrack:linux:unknown]')

title('TOA 3B', 'buildorder')
package = Package.construct_from_compact(setup, 'a')
error, messages2 = obsoleta.buildorder(package)
test_ok(error)
test_eq(messages, messages2)

title('TOA 3C', 'buildorder')
error, messages = obsoleta.buildorder('oups')
test_error(ErrorCode.PACKAGE_NOT_FOUND, error.errorcode, messages)

title('TOA 3D', 'buildorder')
error, messages = obsoleta.buildorder('a', True)
test_ok(error)

# find upstream packages, i.e packages that the package argument depend on

title('TOA 4A', 'upstream - a has 4 upstreams')
error, messages = obsoleta.upstreams('a:*::linux')
print(messages)
test_ok(error)
test_eq(str(messages), '[b:2.2.2:anytrack:anyarch:unknown, c:3.3.3:anytrack:anyarch:unknown, '
                       'd:4.4.4:anytrack:linux:unknown, e:5.5.5:anytrack:linux:unknown]')

title('TOA 4B', 'upstream - as TOA 4A')
package = Package.construct_from_compact(setup, 'a:*::linux')

error, messages2 = obsoleta.upstreams(package)
test_ok(error)
test_eq(messages, messages2)

title('TOA 4C', 'upstream - oups not found')
package = Package.construct_from_compact(setup, 'oups:*::linux')
error, messages = obsoleta.upstreams(package)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

title('TOA 4D', 'upstream - oups not found')
error, messages = obsoleta.upstreams('d:::linux')
test_ok(error)
test_eq(messages, [])


# find downstream packages, i.e. packages that depends on the package argument


title('TOA 5A', 'downstream - b is used by downstream a')
error, messages = obsoleta.downstreams('b:*::linux',
                                       DownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown]')

title('TOA 5B', 'downstream - b is used by downstream a (from compact)')
package = Package.construct_from_compact(setup, 'b:*::linux')
error, messages2 = obsoleta.downstreams(package,
                                        DownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(messages, messages2)

title('TOA 5C', 'downstream - oups not found')
package = Package.construct_from_compact(setup, 'oups:*::linux')
error, messages = obsoleta.downstreams(package,
                                       DownstreamFilter.ExplicitReferences)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

title('TOA 5D', 'downstream to f = a (DownstreamFilter.ExplicitReferences)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       DownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(str(messages), '[e:5.5.5:anytrack:linux:unknown]')

title('TOA 5E', 'downstream to f = a, e (DownstreamFilter.FollowDownstream)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       DownstreamFilter.FollowDownstream)
test_ok(error)
test_eq(str(messages), '[e:5.5.5:anytrack:linux:unknown, a:1.1.1:anytrack:linux:unknown]')

title('TOA 5F', 'downstream to f = a (DownstreamFilter.DownstreamOnly)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       DownstreamFilter.DownstreamOnly)
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown]')


def bump(compact, path, compact_all_arch=None, skip_ranged_versions=False):
    populate_local_temp(path)
    args.set_skip_bumping_ranged_versions(skip_ranged_versions)
    obsoleta = ObsoletaApi(setup, args)
    package = Package.construct_from_compact(setup, compact)

    # establish a new version number to use
    error, package = obsoleta.find_first_package(package, strict=False)
    test_ok(error)
    old_ver = package.get_version()
    version = Version(old_ver).increase(Position.BUILD)
    test_true(old_ver != version, 'version update')

    if compact_all_arch:
        package = Package.construct_from_compact(setup, compact_all_arch)

    # .. and make the bump
    error, result = obsoleta.bump(package, version)
    test_ok(error)

    args.set_skip_bumping_ranged_versions(False)

    # use a check() to verify that the bump was a success
    obsoleta = ObsoletaApi(setup, args)
    error, messages = obsoleta.check(compact)
    test_ok(error)
    return result


title('TOA 6A', 'bump slot - b')
message = bump('b', 'testdata/G2_test_slot')
test_eq(message, ['bumped upstream "b" (b:2.2.2:anytrack:anyarch:unknown) from 2.2.2 to 2.2.3 in "b"',
                  'bumped downstream "a" (b:*:anytrack:anyarch:unknown) from 2.2.2 to 2.2.3 in "a"'])

title('TOA 6B', 'bump slot - d:::linux')
message = bump('d:::linux', 'testdata/G2_test_slot')
test_eq(message, ['bumped upstream "d" (d:4.4.4:anytrack:linux:unknown) from 4.4.4 to 4.4.5 in "d"',
                  'bumped downstream "a" (d:*:anytrack:linux:unknown) from 4.4.4 to 4.4.5 in "a"'])

title('TOA 6C', 'bump multislot')
message = bump('b:::windows', 'testdata/G1_test_multislot')
test_eq(message,
    ['bumped upstream "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumped downstream "a" (b:*:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "a"'])

title('TOA 6D', 'bump multislot with "b:::all"')
message = bump('b', 'testdata/G1_test_multislot', 'b:::all')
print(message)
test_eq(message,
    ['bumped upstream "b" (b:1.1.1:anytrack:linux:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'no {b:1.1.1:anytrack:linux:unknown} downstream packages found',
     'bumped upstream "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumped downstream "a" (b:*:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "a"'])

title('TOA 6E', 'bump multislot for y:::windows (y is a windows only package found in "b" windows slot depends list)')
message = bump('y', 'testdata/G1_test_multislot', 'y:::windows')
print(message)
test_eq(message,
    ['bumped upstream "y" (y:8.8.8:anytrack:windows:unknown) from 8.8.8 to 8.8.9 in "y_windows"',
     'bumped downstream "b" (y:*:anytrack:windows:unknown) from 8.8.8 to 8.8.9 in "b_multi_out_of_source"'])

title('TOA 6F', 'bump multislot for z (but downstream "b" will not be bumped for z since z has a bump:false)')
message = bump('z', 'testdata/G1_test_multislot')
print(message)
test_eq(message,
    ['bumped upstream "z" (z:99.99.99:anytrack:anyarch:unknown) from 99.99.99 to 99.99.100 in "z_anyarch"',
     'skipped downstream "b" (z:99.99.99:anytrack:anyarch:unknown) from >=99 to 99.99.100 in "z_anyarch". bump=True, skipranged=False',
     'skipped downstream "b" (z:99.99.99:anytrack:anyarch:unknown) from >=99 to 99.99.100 in "z_anyarch". bump=True, skipranged=False'])

title('TOA 6G', 'bump multislot for w (but downstream "b" will not be bumped for w since skip_bumping_ranged_versions=True)')
message = bump('w', 'testdata/G1_test_multislot', skip_ranged_versions=True)
print(message)
test_eq(message,
    ['bumped upstream "w" (w:88.88.88:anytrack:anyarch:unknown) from 88.88.88 to 88.88.89 in "w"',
     'skipped downstream "b" (w:88.88.88:anytrack:anyarch:unknown) from >=88 to 88.88.89 in "w". bump=False, skipranged=True',
     'skipped downstream "b" (w:88.88.88:anytrack:anyarch:unknown) from >=88 to 88.88.89 in "w". bump=False, skipranged=True'])

# ---------------------------------------------------------------

populate_local_temp('testdata/G1_test_multislot')

obsoleta = ObsoletaApi(setup, args)

title('TOA 7', 'select a multislot from path and keypath rather than a compact package name')
package = Package.construct_from_package_path(
    setup,
    'local/temp/b_multi_out_of_source',
    keypath='build_linux')
error, messages = obsoleta.tree(package)
test_eq(str(messages), "['b:1.1.1:anytrack:linux:unknown', '  c:2.2.2:anytrack:linux:unknown',"
                       " '  x:3.2.1:anytrack:anyarch:unknown', '  w:88.88.88:anytrack:anyarch:unknown',"
                       " '  z:99.99.99:anytrack:anyarch:unknown']")
test_ok(error)

title('TOA 7b', 'select a multislot from path and key rather than a compact package name')
package = Package.construct_from_package_path(
    setup,
    'local/temp/b_multi_out_of_source',
    key='nix')
error, messages = obsoleta.tree(package)
test_eq(str(messages), "['b:1.1.1:anytrack:linux:unknown', '  c:2.2.2:anytrack:linux:unknown', '  x:3.2.1:anytrack:anyarch:unknown', '  w:88.88.88:anytrack:anyarch:unknown', '  z:99.99.99:anytrack:anyarch:unknown']")
test_ok(error)


title('TOA 8a', 'use parse_multislot_directly=True, the actual key files are not used')
populate_local_temp('testdata/G1_test_multislot')
parse_multislot_directly = setup.parse_multislot_directly
setup.parse_multislot_directly = True
os.remove('local/temp/b_multi_out_of_source/build_linux/obsoleta.key')
os.remove('local/temp/b_multi_out_of_source/build_win/obsoleta.key')
error, messages = obsoleta.tree(package)
test_ok(error)
#
title('TOA 8b', 'use parse_multislot_directly=False, the actual key files are required')
populate_local_temp('testdata/G1_test_multislot')
setup.parse_multislot_directly = False
error, messages = obsoleta.tree(package)
test_ok(error)
setup.parse_multislot_directly = parse_multislot_directly
