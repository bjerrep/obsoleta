#!/usr/bin/env python3
from test_common import title, test_eq, populate_local_temp
from dixi_api import DixiApi
from common import Param, Setup, Position
from log import logger
import logging
from version import Version

logger.setLevel(logging.INFO)

package_dir = populate_local_temp('testdata/G2_test_slot/a')

param = Param()
param.set_depth(2)
param.set_root(package_dir)

# set version

title('TDA_1A', 'set_version/save/get_version')
package_dir = populate_local_temp('testdata/G2_test_slot/a')
dixi = DixiApi(Setup('testdata/test.conf'), param)
dixi.load(package_dir)
old_version, new_version = dixi.set_version(Version('100.100.100'))
test_eq(old_version == '1.1.1')
test_eq(new_version == '100.100.100')
version = dixi.get_version()
test_eq(version == '100.100.100')
dixi.save()
# now reload and check that the package file was indeed saved
dixi = DixiApi(Setup('testdata/test.conf'), param)
dixi.load(package_dir)
version = dixi.get_version()
test_eq(version == '100.100.100')


title('TDA_2', 'incversion - semver')
package_dir = populate_local_temp('testdata/G2_test_slot/a')
dixi = DixiApi(Setup('testdata/test.conf'), param)
dixi.setup.semver = True
dixi.load(package_dir)
old_version, new_version = dixi.dixi.version_digit_increment(Position.MINOR)
test_eq(old_version == '1.1.1')
test_eq(new_version == '1.2.0')


title('TDA_3A', 'call print() on multislotted package with keypath to use')
package_dir = populate_local_temp('testdata/dixi/multislot')
param.set_keypath('build_a')
dixi = DixiApi(Setup('testdata/test.conf'), param)
dixi.load(package_dir)
result = dixi.print()
param.set_keypath(None)
test_eq(result == """{
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
}""")

title('TDA_3B', 'call print() on multislotted package without a keypath fails')
package_dir = populate_local_temp('testdata/dixi/multislot')
dixi = DixiApi(Setup('testdata/test.conf'), param)
dixi.load(package_dir)
result = dixi.print()
test_eq(result == 'need the key for slot/multislot package merge')
