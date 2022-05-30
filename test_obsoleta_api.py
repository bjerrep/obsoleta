#!/usr/bin/env python3
from test_common import title, test_true, test_ok, test_eq, test_error, populate_local_temp
from common import Position, Conf
from obsoleta_api import Args, ObsoletaApi
from obsoletacore import UpDownstreamFilter
from errorcodes import ErrorCode
from version import Version
from package import Package
import os

args = Args()
args.set_depth(2)
args.set_root('local/temp')
# args.set_info_logging()
conf = Conf('testdata/test.conf')

populate_local_temp('testdata/G2_test_slot')
obsoleta = ObsoletaApi(conf, args)

# check

title('TOA 1A', 'check')
package = Package.construct_from_compact(conf, 'a')
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
package = Package.construct_from_compact(conf, 'a')
error, messages = obsoleta.tree(package)
test_ok(error, messages)

title('TOA 2C', 'tree')
error, messages = obsoleta.tree('oups')
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

# buildorder

title('TOA 3A', 'buildorder')
errors, messages = obsoleta.buildorder('a')
test_ok(errors[0])
test_eq(str(messages),
        '[b:2.2.2:anytrack:anyarch:unknown, c:3.3.3:anytrack:anyarch:unknown, '
        'd:4.4.4:anytrack:linux:unknown, f:6.6.6:anytrack:linux:unknown, '
        'e:5.5.5:anytrack:linux:unknown, a:1.1.1:anytrack:linux:unknown]')

title('TOA 3B', 'buildorder')
package = Package.construct_from_compact(conf, 'a')
errors, messages2 = obsoleta.buildorder(package)
test_ok(errors[0])
test_eq(messages, messages2)

title('TOA 3C', 'buildorder')
errors, messages = obsoleta.buildorder('oups')
test_error(ErrorCode.PACKAGE_NOT_FOUND, errors[0].errorcode, messages)

title('TOA 3D', 'buildorder')
errors, messages = obsoleta.buildorder('a', True)
test_ok(errors[0])

# find upstream packages, i.e packages that the package argument depend on

title('TOA 4A', 'upstream - a has 4 directly listed upstreams')
error, messages = obsoleta.upstreams('a:*::linux', UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(str(messages), '[b:2.2.2:anytrack:anyarch:unknown, c:3.3.3:anytrack:anyarch:unknown,'
                       ' d:4.4.4:anytrack:linux:unknown, e:5.5.5:anytrack:linux:unknown]')

title('TOA 4A2', 'upstream - a has 5 upstreams in total')
error, messages_4A2 = obsoleta.upstreams('a:*::linux')
test_ok(error)
test_eq(str(messages_4A2), '[b:2.2.2:anytrack:anyarch:unknown, c:3.3.3:anytrack:anyarch:unknown,'
                           ' d:4.4.4:anytrack:linux:unknown, e:5.5.5:anytrack:linux:unknown,'
                           ' f:6.6.6:anytrack:linux:unknown]')

title('TOA 4B', 'upstream - as TOA 4A')
package = Package.construct_from_compact(conf, 'a:*::linux')
error, messages2 = obsoleta.upstreams(package, UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(messages, messages2)

title('TOA 4B2', 'upstream - f has no upstreams')
package = Package.construct_from_compact(conf, 'f:::linux')
error, messages = obsoleta.upstreams(package)
test_ok(error)
test_eq(messages, [])

title('TOA 4C', 'upstream - oups not found')
package = Package.construct_from_compact(conf, 'oups:*::linux')
error, messages = obsoleta.upstreams(package)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

title('TOA 4D', 'upstream - oups not found')
error, messages = obsoleta.upstreams('d:::linux')
test_ok(error)
test_eq(messages, [])


# find downstream packages, i.e. packages that depends on the package argument

title('TOA 5A', 'downstream - b is used by downstream a')
error, messages = obsoleta.downstreams('b:*::linux',
                                       UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown]')

title('TOA 5B', 'downstream - b is used by downstream a (from compact)')
package = Package.construct_from_compact(conf, 'b:*::linux')
error, messages2 = obsoleta.downstreams(package,
                                        UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(messages, messages2)

#

title('TOA 5A2', 'downstream - a has no downstreams')
error, messages = obsoleta.downstreams('a:*::linux',
                                       UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(messages, [])

#

title('TOA 5C', 'downstream - oups not found')
package = Package.construct_from_compact(conf, 'oups:*::linux')
error, messages = obsoleta.downstreams(package,
                                       UpDownstreamFilter.ExplicitReferences)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

#

title('TOA 5D', 'downstream to f = a (UpDownstreamFilter.ExplicitReferences)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       UpDownstreamFilter.ExplicitReferences)
test_ok(error)
test_eq(str(messages), '[e:5.5.5:anytrack:linux:unknown]')

title('TOA 5E', 'downstream to f = a, e (UpDownstreamFilter.FollowTree)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       UpDownstreamFilter.FollowTree)
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown, e:5.5.5:anytrack:linux:unknown]')

title('TOA 5F', 'downstream to f = a (UpDownstreamFilter.TreeOnly)')
error, messages = obsoleta.downstreams('f:*::linux',
                                       UpDownstreamFilter.TreeOnly)
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown]')


# TOA FFP : find first package

populate_local_temp('testdata/C5_test_multiple_versions')
obsoleta = ObsoletaApi(conf, args)

title('TOA FFP_A', 'find first package, strict=False')
error, messages = obsoleta.find_first_package('c')
test_ok(error)
test_eq(str(messages), 'c:1.2.4:production:anyarch:unknown')

title('TOA FFP_B', 'find first package, strict=True so this will fail')
error, messages = obsoleta.find_first_package('c', strict=True)
test_error(error, ErrorCode.PACKAGE_NOT_UNIQUE)
test_eq(str(messages), '[c:1.2.4:production:anyarch:unknown, c:1.2.3:production:anyarch:unknown]')


# bump

def test_bump(compact, path, bump=False, skip_ranged_versions=False, package_for_check=None, dryrun=False):
    populate_local_temp(path)
    args.set_skip_bumping_ranged_versions(skip_ranged_versions)
    obsoleta = ObsoletaApi(conf, args)
    target_package = Package.construct_from_compact(conf, compact)

    # establish a new version number to use
    error, package = obsoleta.find_first_package(target_package, strict=False)
    test_ok(error)
    old_ver = package.get_version()
    version = Version(old_ver).increase(Position.BUILD)
    test_true(old_ver != version, 'version update')

    # .. and make the bump
    error, result = obsoleta.bump(target_package, version, bump=bump, dryrun=dryrun)
    test_ok(error)

    args.set_skip_bumping_ranged_versions(False)

    # use a check() to verify that the bump was a success
    obsoleta = ObsoletaApi(conf, args)
    if package_for_check:
        error, messages = obsoleta.check(package_for_check)
    else:
        error, messages = obsoleta.check(compact)
    test_ok(error)
    return result


populate_local_temp('testdata/G2_test_slot')
obsoleta = ObsoletaApi(conf, args)

title('TOA 6A', 'bump slot - b')
message = test_bump('b', 'testdata/G2_test_slot')
test_eq(message,
    ['bumping package "b" (b:2.2.2:anytrack:anyarch:unknown) from 2.2.2 to 2.2.3 in "b"',
     'bumping dependency b:2.2.2:anytrack:anyarch:unknown in downstream "a" from 2.2.2 to 2.2.3 in "a" (slot "nix")'])

title('TOA 6A2', 'bump slot - b - dryrun')
message = test_bump('b', 'testdata/G2_test_slot')
test_eq(message,
    ['bumping package "b" (b:2.2.2:anytrack:anyarch:unknown) from 2.2.2 to 2.2.3 in "b"',
     'bumping dependency b:2.2.2:anytrack:anyarch:unknown in downstream "a" from 2.2.2 to 2.2.3 in "a" (slot "nix")'])
error, tree_list = obsoleta.tree('a')
test_eq(tree_list,
    ['a:1.1.1:anytrack:linux:unknown',
     '  b:2.2.2:anytrack:anyarch:unknown',
     '  c:3.3.3:anytrack:anyarch:unknown',
     '  d:4.4.4:anytrack:linux:unknown',
     '  e:5.5.5:anytrack:linux:unknown',
     '    f:6.6.6:anytrack:linux:unknown'])

title('TOA 6B', 'bump slot - d:::linux')
message = test_bump('d:::linux', 'testdata/G2_test_slot')
test_eq(message,
    ['bumping package "d" (d:4.4.4:anytrack:linux:unknown) from 4.4.4 to 4.4.5 in "d"',
     'bumping dependency d:4.4.4:anytrack:linux:unknown in downstream "a" from 4.4.4 to 4.4.5 in "a" (slot "nix")'])

title('TOA 6B2', 'bump f')
message = test_bump('f', 'testdata/G2_test_slot', bump=True, package_for_check='a')
test_eq(message,
    ['bumping package "f" (f:6.6.6:anytrack:linux:unknown) from 6.6.6 to 6.6.7 in "f"',
     'bumping dependency f:6.6.6:anytrack:linux:unknown in downstream "e" from 6.6.6 to 6.6.7 in "e"',
     'bumping package "e" (e:5.5.5:anytrack:linux:unknown) from 5.5.5 to 5.5.6 in "e"',
     'bumping dependency e:5.5.5:anytrack:linux:unknown in downstream "a" from 5.5.5 to 5.5.6 in "a" (slot "nix")',
     'bumping package "a" (a:1.1.1:anytrack:linux:unknown) from 1.1.1 to 1.1.2 in "a"'])

title('TOA 6B3', 'bump f')
message = test_bump('f', 'testdata/G2_test_slot', package_for_check='a')
test_eq(message,
    ['bumping package "f" (f:6.6.6:anytrack:linux:unknown) from 6.6.6 to 6.6.7 in "f"',
     'bumping dependency f:6.6.6:anytrack:linux:unknown in downstream "e" from 6.6.6 to 6.6.7 in "e"'])

title('TOA 6C', 'bump multislot')
message = test_bump('b:::windows', 'testdata/G1_test_multislot', package_for_check='a')
test_eq(message,
    ['bumping package "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping dependency b:1.1.1:anytrack:windows:unknown in downstream "a" from 1.1.1 to 1.1.2 in "a"'])

title('TOA 6D', 'bump multislot for "b"')
message = test_bump('b', 'testdata/G1_test_multislot', bump=True, package_for_check='a')
test_eq(message,
    ['bumping package "b" (b:1.1.1:anytrack:linux:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping package "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping dependency b:1.1.1:anytrack:windows:unknown in downstream "a" from 1.1.1 to 1.1.2 in "a"',
     'bumping package "a" (a:0.0.0:anytrack:windows:unknown) from 0.0.0 to 0.0.1 in "a"'])

title('TOA 6D2', 'bump multislot with "b" i.e for all archs')
message = test_bump('b', 'testdata/G1_test_multislot')
test_eq(message,
    ['bumping package "b" (b:1.1.1:anytrack:linux:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping package "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping dependency b:1.1.1:anytrack:windows:unknown in downstream "a" from 1.1.1 to 1.1.2 in "a"'])

title('TOA 6E', 'bump multislot for y:::windows (y is a windows only package found in "b" windows slot depends list)')
message = test_bump('y:::windows', 'testdata/G1_test_multislot', bump=True)
test_eq(message,
    ['bumping package "y" (y:8.8.8:anytrack:windows:unknown) from 8.8.8 to 8.8.9 in "y_windows"',
     'bumping dependency y:8.8.8:anytrack:windows:unknown in downstream "b" from 8.8.8 to 8.8.9 in "b_multi_out_of_source" (slot "win")',
     'bumping package "b" (b:1.1.1:anytrack:windows:unknown) from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
     'bumping dependency b:1.1.1:anytrack:windows:unknown in downstream "a" from 1.1.1 to 1.1.2 in "a"',
     'bumping package "a" (a:0.0.0:anytrack:windows:unknown) from 0.0.0 to 0.0.1 in "a"'])

title('TOA 6F', 'bump multislot for z (but downstream "b" will not be bumped for z since z has a bump:false)')
message = test_bump('z', 'testdata/G1_test_multislot')
test_eq(message,
    ['bumping package "z" (z:99.99.99:anytrack:anyarch:unknown) from 99.99.99 to 99.99.100 in "z_anyarch"',
     'skipped downstream "b:1.1.1:anytrack:linux:unknown" (z:99.99.99:anytrack:anyarch:unknown) from 1.1.1 to 99.99.100 in "b_multi_out_of_source". Reason: BUMPFALSE',
     'skipped downstream "b:1.1.1:anytrack:windows:unknown" (z:99.99.99:anytrack:anyarch:unknown) from 1.1.1 to 99.99.100 in "b_multi_out_of_source". Reason: BUMPFALSE'])

title('TOA 6G', 'bump multislot for w (but downstream "b" will not be bumped for w since skip_bumping_ranged_versions=True)')
message = test_bump('w', 'testdata/G1_test_multislot', skip_ranged_versions=True)
test_eq(message,
    ['bumping package "w" (w:88.88.88:anytrack:anyarch:unknown) from 88.88.88 to 88.88.89 in "w"',
     'skipped downstream "b:1.1.1:anytrack:linux:unknown" (w:88.88.88:anytrack:anyarch:unknown) from 1.1.1 to 88.88.89 in "b_multi_out_of_source". Reason: SKIPRANGED',
     'skipped downstream "b:1.1.1:anytrack:windows:unknown" (w:88.88.88:anytrack:anyarch:unknown) from 1.1.1 to 88.88.89 in "b_multi_out_of_source". Reason: SKIPRANGED'])

# ---------------------------------------------------------------

populate_local_temp('testdata/G1_test_multislot')
obsoleta = ObsoletaApi(conf, args)


title('TOA 7', 'select a multislot from path and keypath rather than a compact package name')
package = Package.construct_from_package_path(
    conf,
    'local/temp/b_multi_out_of_source',
    keypath='build_linux')
error, messages = obsoleta.tree(package)
test_ok(error)
test_eq(messages,
        ['b:1.1.1:anytrack:linux:unknown',
         '  c:2.2.2:anytrack:linux:unknown',
         '  w:88.88.88:anytrack:anyarch:unknown',
         '  x:3.2.1:anytrack:anyarch:unknown',
         '  y:8.8.8:anytrack:linux:unknown',
         '  z:99.99.99:anytrack:anyarch:unknown'])

title('TOA 7b', 'select a multislot from path and key rather than a compact package name')
package = Package.construct_from_package_path(
    conf,
    'local/temp/b_multi_out_of_source',
    key='nix')
error, messages = obsoleta.tree(package)
test_eq(messages,
    ['b:1.1.1:anytrack:linux:unknown',
     '  c:2.2.2:anytrack:linux:unknown',
     '  w:88.88.88:anytrack:anyarch:unknown',
     '  x:3.2.1:anytrack:anyarch:unknown',
     '  y:8.8.8:anytrack:linux:unknown',
     '  z:99.99.99:anytrack:anyarch:unknown'])
test_ok(error)


populate_local_temp('testdata/G1_test_multislot')
obsoleta = ObsoletaApi(conf, args)


title('TOA 8a', 'use parse_multislot_directly=True, the actual key files are not used')
parse_multislot_directly = conf.parse_multislot_directly
conf.parse_multislot_directly = True
os.remove('local/temp/b_multi_out_of_source/build_linux/obsoleta.key')
os.remove('local/temp/b_multi_out_of_source/build_win/obsoleta.key')
error, messages = obsoleta.tree(package)
test_ok(error)
#

populate_local_temp('testdata/G1_test_multislot')
obsoleta = ObsoletaApi(conf, args)


title('TOA 8b', 'use parse_multislot_directly=False, the actual key files are required')
conf.parse_multislot_directly = False
error, messages = obsoleta.tree(package)
test_ok(error)
conf.parse_multislot_directly = parse_multislot_directly


populate_local_temp('testdata/B5_test_missing_package')
obsoleta = ObsoletaApi(conf, args)


title('TOA 9A', 'upstream() using ExplicitReferences will not discover the missing upstream package "c" required by "b"')
error, messages = obsoleta.upstreams('a', UpDownstreamFilter.ExplicitReferences)
test_eq(str(messages), '[b:0.1.0:testing:anyarch:unknown]')
test_ok(error)


title('TOA 9B', 'upstream fails with missing package "c" required by "b" with default filter FollowTree')
error, messages = obsoleta.upstreams('a')
test_eq('Package not found: c:1.2.3:production:anyarch:unknown from parent b:0.1.0:testing:anyarch:unknown',
        error.to_string())
test_error(error.get_errorcode(), ErrorCode.PACKAGE_NOT_FOUND)


title('TOA 10', 'Test that the switch "keep_track" makes it impossible to resolve "y" ("a" is testing but "y" only exists as production')
# getting started, "y" in testing is happy to find an "y" in production
populate_local_temp('testdata/A4_dont_get_confused')
obsoleta = ObsoletaApi(conf, args)
error, messages = obsoleta.tree('a')
test_eq(messages,
        ['a:0.1.2:testing:linux_x86_64:unknown',
         '  x:2.2.2:testing:linux_x86_64:unknown',
         '  y:3.3.3:production:linux_x86_64:unknown'])
test_ok(error)
#
# "y" dependency in testing has keeptrack:true and refuses to use the single "y" in production
error, messages = obsoleta.tree('b')
test_error(error.get_errorcode(), ErrorCode.PACKAGE_NOT_FOUND)
#
# reload with a configuration file setting the global keep_track to true. Same result as above.
keep_track_conf = Conf('testdata/test_keep_track.conf')
obsoleta = ObsoletaApi(keep_track_conf, args)
error, messages = obsoleta.tree('a')
test_error(error.get_errorcode(), ErrorCode.PACKAGE_NOT_FOUND)


# TOA : tests with allow_duplicates=True from either configuration file or from package attributes
# This will for all trivial binary linking result in ABI rubbish

populate_local_temp('testdata/C5_test_multiple_versions')
conf.allow_duplicates = True
obsoleta = ObsoletaApi(conf, args)

title('TOA 11A', 'allow_duplicates=True so package c will be resolved with two versions')
errors, messages = obsoleta.buildorder('a')
test_ok(errors[0])
test_eq(str(messages),'[c:1.2.3:production:anyarch:unknown, c:1.2.4:production:anyarch:unknown, \
d:1.2.3:production:anyarch:unknown, b:0.1.0:testing:anyarch:unknown, a:0.1.2:development:anyarch:unknown]')
conf.allow_duplicates = False


title('TOA 11B', 'package c has key:value "allow_duplicates=true" so package c will be succesfully resolved with two versions')
populate_local_temp('testdata/C6_test_multiple_versions_with_allow_duplicates')
obsoleta = ObsoletaApi(conf, args)
errors, messages = obsoleta.buildorder('a')
test_ok(errors[0])
test_eq(str(messages),'[c:1.2.3:production:anyarch:unknown, c:1.2.4:production:anyarch:unknown, \
d:1.2.3:production:anyarch:unknown, b:0.1.0:testing:anyarch:unknown, a:0.1.2:development:anyarch:unknown]')

