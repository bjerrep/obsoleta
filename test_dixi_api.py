#!/usr/bin/env python3
from test_common import title, test_eq, populate_local_temp
from dixi_api import DixiApi
from common import Args, Setup, Position
from dixicore import TrackSetScope
from package import Package, Track
from log import logger
import dixi_find_best
import exceptions, errorcodes
from version import Version
import logging


logger.setLevel(logging.INFO)

args = Args()
args.set_depth(2)
setup = Setup('testdata/test.conf')

# set version

title('TDA_1A', 'set_version/save/get_version')
package_dir = populate_local_temp('testdata/G2_test_slot/a')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
old_version, new_version = dixi.set_version(Version('100.100.100'))
test_eq(old_version, '1.1.1')
test_eq(new_version, '100.100.100')
version = dixi.get_version()
test_eq(version, '100.100.100')
dixi.save()
# now reload and check that the package file was indeed saved
dixi = DixiApi(setup, args)
dixi.load(package_dir)
version = dixi.get_version()
test_eq(version, '100.100.100')


title('TDA_2', 'incversion - semver')
package_dir = populate_local_temp('testdata/G2_test_slot/a')
dixi = DixiApi(setup, args)
dixi.setup.semver = True
dixi.load(package_dir)
old_version, new_version = dixi.dixi.version_digit_increment(Position.MINOR)
test_eq(old_version, '1.1.1')
test_eq(new_version, '1.2.0')


title('TDA_3A', 'call print() on multislotted package with keypath to use')
package_dir = populate_local_temp('testdata/dixi/multislot')
args.set_slot_path('build_a')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
result = dixi.print()
args.set_slot_path(None)
test_eq(result == """{
  "name": "a",
  "version": "0.1.2",
  "arch": "x86_64",
  "depends": [
    {
      "name": "b",
      "version": "2.2.2",
      "arch": "x86_64"
    },
    {
      "name": "c",
      "version": "3.3.3",
      "track": "production",
      "arch": "x86_64"
    }
  ]
}""")


title('TDA_3B', 'call print() on multislotted package without a keypath fails')
package_dir = populate_local_temp('testdata/dixi/multislot')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
result = dixi.print()
test_eq(result == 'need the key for slot/multislot package merge')


def get_p(name):
    return dixi.dixi.package.find_dependency(Package.construct_from_compact(setup, name))


title('TDA_4A', 'set track - downstream')
package_dir = populate_local_temp('testdata/dixi/simple')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
dixi.set_track(Track.testing, TrackSetScope.DOWNSTREAM)
track_a = dixi.get_track()
track_b = dixi.get_track('b')
track_c = dixi.get_track('c')
test_eq(track_a, 'testing')
test_eq(track_b, 'development')
test_eq(track_c, 'production')

title('TDA_4B', 'set track - upgrade')
package_dir = populate_local_temp('testdata/dixi/simple')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
dixi.set_track(Track.testing, TrackSetScope.UPGRADE)
track_a = dixi.get_track()
track_b = dixi.get_track('b')
track_c = dixi.get_track('c')
test_eq(track_a, 'testing')
test_eq(track_b, 'testing')
test_eq(track_c, 'production')

title('TDA_4C', 'set track - force')
package_dir = populate_local_temp('testdata/dixi/simple')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
dixi.set_track(Track.testing, TrackSetScope.FORCE)
track_a = dixi.get_track()
track_b = dixi.get_track('b')
track_c = dixi.get_track('c')
test_eq(track_a, 'testing')
test_eq(track_b, 'testing')
test_eq(track_c, 'testing')


title('TDA_4D', 'set track - force/slotted')
package_dir = populate_local_temp('testdata/dixi/multislot')
args.set_slot_path('build_a')
#
dixi = DixiApi(setup, args)
dixi.load(package_dir)
dixi.set_track(Track.testing, TrackSetScope.FORCE)
track_a = dixi.get_track()
track_b = dixi.get_track('b')
track_c = dixi.get_track('c')
test_eq(track_a, 'testing')
test_eq(track_b, 'testing')
test_eq(track_c, 'testing')
dixi.save()
# Try to save and reload and do the check again
dixi = DixiApi(setup, args)
dixi.load(package_dir)
track_a = dixi.get_track()
track_b = dixi.get_track('b')
track_c = dixi.get_track('c')
test_eq(track_a, 'testing')
test_eq(track_b, 'testing')
test_eq(track_c, 'testing')
args.set_slot_path(None)


title('TDA_5', 'setvalue and getvalue in depends section')
package_dir = populate_local_temp('testdata/dixi/simple')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
depends_package = Package.construct_from_compact(setup, 'b')
# get current version for 'b' (note that there is a dedicated get_version())
_version = dixi.get_value('version', depends_package)
test_eq(_version, '0.1.3')
# change the version for 'b' and verify
dixi.set_value('version', '1.1.1', depends_package)
_version = dixi.get_value('version', depends_package)
test_eq(_version, '1.1.1')
# get a nonexistent value
_value = dixi.get_value('nah', depends_package)
test_eq(_value, None)
# get a boolean set to False
_value = dixi.get_value('what_about_a_boolean', depends_package)
test_eq(_value, False)


title('TDA_6', 'readonly package handling')
package_dir = populate_local_temp('testdata/A2_test_simple/a')
dixi = DixiApi(setup, args)
dixi.load(package_dir)
dixi.set_readonly()
dixi.set_readonly(False)
dixi.set_readonly()
dixi.save()
dixi.load(package_dir)
try:
    dixi.set_value('version', '3.2.1')
    raise exceptions.ObsoletaException('test_dixi_api', errorcodes.ErrorCode.TEST_FAILED)
except exceptions.ModifyingReadonlyPackage:
    pass


title('TDA_DFB', 'dixi find best utility script')
with open('testdata/dixi/dixi_find_files/candidates') as f:
    candidates = f.readlines()
package = Package.construct_from_compact(setup, 'a:1.1.>=2:anytrack:anyarch:unknown')
best_candidate = dixi_find_best.find_best_candidate(setup, package, candidates)
test_eq(best_candidate.to_compact_string(), 'a:1.1.3:anytrack:anyarch:unknown')
