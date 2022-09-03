#!/usr/bin/env python3
"""
Unittesting of obsoletacore.
"""
import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from obsoleta.test.test_common import TESTDATA_PATH, title, test_eq
from obsoleta.common import Conf
from obsoleta.obsoleta_api import Args
import obsoleta.obsoletacore as core

args = Args()
args.set_depth(2)
args.set_info_logging()
conf = Conf(f'{TESTDATA_PATH}/test.conf')

# coincident root paths with a distance above the depth should be preserved
conf.depth = 2

# construct an Obsoleta object but do not run the initializer __init__
obsoleta = core.Obsoleta.__new__(core.Obsoleta)
obsoleta.args = args
obsoleta.conf = conf

# ----------------------------------------------------------------

title('TOCORE 1', 'construct_root_list, remove duplicates')

PATH1 = '/here/we/go'
PATH2 = '/here/we/go'

obsoleta.conf.paths = [PATH1, PATH2]
roots = obsoleta.construct_root_list()
test_eq(roots, [PATH1])


PATH1 = '/here/we/go'
PATH2 = '/here/we/go2'

obsoleta.conf.paths = [PATH1, PATH2]
roots = obsoleta.construct_root_list()
test_eq(roots, [PATH1, PATH2])


PATH1 = '/here/we/go'
PATH2 = '/here/we/go/deleteme'

obsoleta.conf.paths = [PATH1, PATH2]
roots = obsoleta.construct_root_list()
test_eq(roots, [PATH1])

PATH1 = '/here/we/go'
PATH2 = '/here/we/go/sub1/deleteme'

obsoleta.conf.paths = [PATH1, PATH2]
roots = obsoleta.construct_root_list()
test_eq(roots, [PATH1])

PATH1 = '/here/we/go'
PATH2 = '/here/we/go/sub1/sub2/keepme'

obsoleta.conf.paths = [PATH1, PATH2]
roots = obsoleta.construct_root_list()
test_eq(roots, [PATH1, PATH2])
