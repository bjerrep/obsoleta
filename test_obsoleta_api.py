#!/usr/bin/env python3
from test_common import execute, title, test_true, test_ok, test_eq, test_error, populate_local_temp
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
package = obsoleta.make_package_from_compact('a')
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
package = obsoleta.make_package_from_compact('a')
error, messages2 = obsoleta.buildorder(package)
test_ok(error)
test_eq(messages, messages2)

title('TOA 3C', 'buildorder')
error, messages = obsoleta.buildorder('oups')
test_error(error, ErrorCode.RESOLVE_ERROR, messages)

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
package = obsoleta.make_package_from_compact('a:*::linux')
error, messages2 = obsoleta.upstreams(package)
test_ok(error)
test_eq(messages, messages2)

title('TOA 4C', 'upstream - oups not found')
package = obsoleta.make_package_from_compact('oups:*::linux')
error, messages = obsoleta.upstreams(package)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)

title('TOA 4D', 'upstream - oups not found')
error, messages = obsoleta.upstreams('d:::linux')
test_ok(error)
test_eq(messages, [])


# find downstream packages, i.e. packages that depends on the package argument

title('TOA 5A', 'downstream - b is used by downstream a')
error, messages = obsoleta.downstreams('b:*::linux')
test_ok(error)
test_eq(str(messages), '[a:1.1.1:anytrack:linux:unknown]')

title('TOA 5B', 'downstream - b is used by downstream a')
package = obsoleta.make_package_from_compact('b:*::linux')
error, messages2 = obsoleta.downstreams(package)
test_ok(error)
test_eq(messages, messages2)

title('TOA 5C', 'downstream - oups not found')
package = obsoleta.make_package_from_compact('oups:*::linux')
error, messages = obsoleta.downstreams(package)
test_error(error, ErrorCode.PACKAGE_NOT_FOUND, messages)


def bump(compact, path):
    populate_local_temp(path)
    obsoleta = ObsoletaApi(setup, param)
    package = obsoleta.make_package_from_compact(compact)

    # establish a new version number to use
    package = obsoleta.find_package(package)
    old_ver = package.get_version()
    new_ver = Version(old_ver).increase(Position.BUILD)
    test_true(old_ver != new_ver, 'version update')

    # .. and make the bump
    error, result = obsoleta.bump(package, new_ver)
    test_ok(error)

    # use a check() to verify that the bump was a success
    obsoleta = ObsoletaApi(setup, param)
    error, messages = obsoleta.check(compact)
    test_ok(error)
    return result


title('TOA 6A', 'bump slot - b')
message = bump('b', 'testdata/G2_test_slot')
test_eq(message, [
    'bumped upstream {b:2.2.2:anytrack:anyarch:unknown} from 2.2.2 to 2.2.3 in "b"',
    'bumped downstream {b:2.2.2:anytrack:linux:unknown} from 2.2.2 to 2.2.3 in "a"'])

title('TOA 6B', 'bump slot - d:::linux')
message = bump('d:::linux', 'testdata/G2_test_slot')
test_eq(message, [
    'bumped upstream {d:4.4.4:anytrack:linux:unknown} from 4.4.4 to 4.4.5 in "d"',
    'bumped downstream {d:4.4.4:anytrack:linux:unknown} from 4.4.4 to 4.4.5 in "a"'])

title('TOA 6C', 'bump multislot')
message = bump('b:::windows', 'testdata/G1_test_multislot')
test_eq(message, [
    'bumped upstream {b:1.1.1:anytrack:windows:unknown} from 1.1.1 to 1.1.2 in "b_multi_out_of_source"',
    'bumped downstream {b:1.1.1:anytrack:windows:unknown} from 1.1.1 to 1.1.2 in "a"'])
