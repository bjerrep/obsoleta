#!/usr/bin/env python3
from test_common import execute, title, test_success
from obsoleta_api import Param, ObsoletaApi
from log import logger
import logging

execute('./dixi.py --printkey key:nix > testdata/G2_test_slot/a/obsoleta.key')

logger.setLevel(logging.INFO)

my_root = 'testdata/G2_test_slot'

param = Param()
param.set_depth(2)
param.set_root(my_root)

obsoleta = ObsoletaApi('testdata/test.conf', param)

# check

title('1A', 'check')
package = obsoleta.make_package_from_compact('a')
success, messages = obsoleta.check(package)
test_success(success, messages)

title('1B', 'check')
success, messages = obsoleta.check('e')
test_success(success, messages)

# tree

title('2A', 'tree')
success, messages = obsoleta.tree('a')
test_success(success, messages)

title('2B', 'tree')
package = obsoleta.make_package_from_compact('a')
success, messages = obsoleta.tree(package)
test_success(success, messages)

title('2C', 'tree')
success, messages = obsoleta.tree('oups')
test_success(not success, messages)

# buildorder

title('3A', 'buildorder')
success, messages = obsoleta.buildorder('a')
test_success(success, messages)

title('3B', 'buildorder')
package = obsoleta.make_package_from_compact('a')
success, messages = obsoleta.buildorder(package)
test_success(success, messages)

title('3C', 'buildorder')
success, messages = obsoleta.buildorder('oups')
test_success(not success, messages)

title('3D', 'buildorder')
success, messages = obsoleta.buildorder('a', True)
test_success(success, messages)

# locate

title('4A', 'locate')
success, messages = obsoleta.locate('a:*::linux')
test_success(success, messages)

title('4B', 'locate')
package = obsoleta.make_package_from_compact('a:*::linux')
success, messages = obsoleta.locate(package)
test_success(success, messages)

title('4C', 'locate')
package = obsoleta.make_package_from_compact('oups:*::linux')
success, messages = obsoleta.locate(package)
test_success(not success, messages)

# upstream

title('5A', 'upstream')
success, messages = obsoleta.upstream('b:*::linux')
test_success(success, messages)

title('5B', 'upstream')
package = obsoleta.make_package_from_compact('b:*::linux')
success, messages = obsoleta.upstream(package)
test_success(success, messages)

title('5C', 'upstream')
package = obsoleta.make_package_from_compact('oups:*::linux')
success, messages = obsoleta.upstream(package)
test_success(not success, messages)
