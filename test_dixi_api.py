#!/usr/bin/env python3
from test_common import title, test_eq, populate_local_temp
from dixi_api import DixiApi
from common import Param, Setup
from log import logger
import logging
from version import Version

package_dir = populate_local_temp('testdata/G2_test_slot/a')

logger.setLevel(logging.INFO)

param = Param()
param.set_depth(2)
param.set_root(package_dir)

# set version

title('TDA_1A', 'set_version/save/get_version')
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
