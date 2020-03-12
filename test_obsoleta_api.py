#!/usr/bin/env python3
from test_common import execute, title, test_true, test_ok, test_error, populate_local_temp
from common import Position, Setup
from obsoleta_api import Param, ObsoletaApi
from errorcodes import ErrorCode
from version import Version
from log import logger
import logging

execute('./dixi.py --printkey key:nix > testdata/G2_test_slot/a/obsoleta.key')

logger.setLevel(logging.INFO)

populate_local_temp('testdata/G2_test_slot')

param = Param()
param.set_depth(2)
param.set_root('local/temp')
setup = Setup('testdata/test.conf')

obsoleta = ObsoletaApi(setup, param)

# check

title('1A', 'check')
package = obsoleta.make_package_from_compact('a')
errorcode, messages = obsoleta.check(package)
test_ok(errorcode, messages)

title('1B', 'check')
errorcode, messages = obsoleta.check('e')
test_ok(errorcode, messages)

# tree

title('2A', 'tree')
errorcode, messages = obsoleta.tree('a')
test_ok(errorcode, messages)

title('2B', 'tree')
package = obsoleta.make_package_from_compact('a')
errorcode, messages = obsoleta.tree(package)
test_ok(errorcode, messages)

title('2C', 'tree')
errorcode, messages = obsoleta.tree('oups')
test_error(errorcode, ErrorCode.PACKAGE_NOT_FOUND, messages)

# buildorder

title('3A', 'buildorder')
errorcode, messages = obsoleta.buildorder('a')
test_ok(errorcode, messages)

title('3B', 'buildorder')
package = obsoleta.make_package_from_compact('a')
errorcode, messages = obsoleta.buildorder(package)
test_ok(errorcode, messages)

title('3C', 'buildorder')
errorcode, messages = obsoleta.buildorder('oups')
test_error(errorcode, ErrorCode.RESOLVE_ERROR, messages)

title('3D', 'buildorder')
errorcode, messages = obsoleta.buildorder('a', True)
test_ok(errorcode, messages)

# upstream

title('4A', 'upstream')
errorcode, messages = obsoleta.upstreams('a:*::linux')
test_ok(errorcode, messages)

title('4B', 'upstream')
package = obsoleta.make_package_from_compact('a:*::linux')
errorcode, messages = obsoleta.upstreams(package)
test_ok(errorcode, messages)

title('4C', 'upstream')
package = obsoleta.make_package_from_compact('oups:*::linux')
errorcode, messages = obsoleta.upstreams(package)
test_error(errorcode, ErrorCode.PACKAGE_NOT_FOUND, messages)

# upstream

title('5A', 'downstream')
errorcode, messages = obsoleta.downstreams('b:*::linux')
test_ok(errorcode, messages)

title('5B', 'downstream')
package = obsoleta.make_package_from_compact('b:*::linux')
errorcode, messages = obsoleta.downstreams(package)
test_ok(errorcode, messages)

title('5C', 'downstream')
package = obsoleta.make_package_from_compact('oups:*::linux')
errorcode, messages = obsoleta.downstreams(package)
test_error(errorcode, ErrorCode.PACKAGE_NOT_FOUND, messages)


def bump(compact):
    populate_local_temp('testdata/G2_test_slot')
    obsoleta = ObsoletaApi(setup, param)
    package = obsoleta.make_package_from_compact(compact)
    errorcode, packages = obsoleta.upstreams(package)
    if len(packages) != 1:
        test_true(False, "lookup failed")
    p = packages[0]
    # increase build number ..
    old_ver = p.get_version()
    new_ver = Version(old_ver).increase(Position.BUILD)
    test_true(old_ver != new_ver, 'version update')
    # .. and make the bump
    errorcode, result = obsoleta.bump(package, new_ver)
    test_true(errorcode, result)
    # go through the motions to explicitly verify that the package did in fact get a new version
    obsoleta = ObsoletaApi(setup, param)
    errorcode, packages = obsoleta.upstreams(package)
    test_true(packages[0].get_version() == new_ver, 'new version found')
    # and indirectly check that downstreams were updated as well
    errorcode, messages = obsoleta.check('a')
    test_true(errorcode, messages)


title('6A', 'bump')
bump('b')
