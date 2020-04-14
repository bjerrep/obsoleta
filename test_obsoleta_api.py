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

title('TOA 1A', 'check')
package = obsoleta.make_package_from_compact('a')
errorcode, messages = obsoleta.check(package)
test_ok(errorcode, messages)

title('TOA 1B', 'check')
errorcode, messages = obsoleta.check('e')
test_ok(errorcode, messages)

# tree

title('TOA 2A', 'tree for "a" in G2_test_slot')
error, messages = obsoleta.tree('a')
test_ok(error.get_errorcode(), messages)

title('TOA 2B', 'tree')
package = obsoleta.make_package_from_compact('a')
error, messages = obsoleta.tree(package)
test_ok(error.get_errorcode(), messages)

title('TOA 2C', 'tree')
error, messages = obsoleta.tree('oups')
test_error(error.get_errorcode(), ErrorCode.PACKAGE_NOT_FOUND, messages)

# buildorder

title('TOA 3A', 'buildorder')
error, messages = obsoleta.buildorder('a')
test_ok(error, messages)

title('TOA 3B', 'buildorder')
package = obsoleta.make_package_from_compact('a')
error, messages = obsoleta.buildorder(package)
test_ok(error, messages)

title('TOA 3C', 'buildorder')
error, messages = obsoleta.buildorder('oups')
test_error(error, ErrorCode.RESOLVE_ERROR, messages)

title('TOA 3D', 'buildorder')
error, messages = obsoleta.buildorder('a', True)
test_ok(error, messages)

# upstream

title('TOA 4A', 'upstream')
errorcode, messages = obsoleta.upstreams('a:*::linux')
test_ok(errorcode, messages)

title('TOA 4B', 'upstream')
package = obsoleta.make_package_from_compact('a:*::linux')
errorcode, messages = obsoleta.upstreams(package)
test_ok(errorcode, messages)

title('TOA 4C', 'upstream')
package = obsoleta.make_package_from_compact('oups:*::linux')
errorcode, messages = obsoleta.upstreams(package)
test_error(errorcode, ErrorCode.PACKAGE_NOT_FOUND, messages)

# upstream

title('TOA 5A', 'downstream')
error, messages = obsoleta.downstreams('b:*::linux')
test_ok(error, messages)

title('TOA 5B', 'downstream')
package = obsoleta.make_package_from_compact('b:*::linux')
error, messages = obsoleta.downstreams(package)
test_ok(error, messages)

title('TOA 5C', 'downstream')
package = obsoleta.make_package_from_compact('oups:*::linux')
error, messages = obsoleta.downstreams(package)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)


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
    error, result = obsoleta.bump(package, new_ver)
    test_true(error, result)
    # go through the motions to explicitly verify that the package did in fact get a new version
    obsoleta = ObsoletaApi(setup, param)
    errorcode, packages = obsoleta.upstreams(package)
    test_true(packages[0].get_version() == new_ver, 'new version found')
    # and indirectly check that downstreams were updated as well
    errorcode, messages = obsoleta.check('a')
    test_true(errorcode, messages)


title('TOA 6A', 'bump')
bump('b')
