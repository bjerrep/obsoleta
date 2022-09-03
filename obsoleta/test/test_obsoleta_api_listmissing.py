#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from obsoleta.test.test_common import TESTDATA_PATH, title, test_eq, test_error, populate_local_temp
from obsoleta.common import Conf
from obsoleta.errorcodes import ErrorCode
from obsoleta.obsoleta_api import Args, ObsoletaApi
from obsoleta.package import Package

args = Args()
args.set_depth(2)
args.set_root('local/temp')
#args.set_info_logging()
conf = Conf(f'{TESTDATA_PATH}/test.conf')

title('TOALM 1', 'listmissing in E1_list_missing_packages')
populate_local_temp('E1_list_missing_packages/')
obsoleta = ObsoletaApi(conf, args)

package = Package.construct_from_compact(conf, 'a')
error, missing = obsoleta.list_missing(package)
test_error(error, ErrorCode.RESOLVE_ERROR)
test_eq(str(missing), '[b:1.1.1:anytrack:c64:unknown, e:1.1.1:anytrack:c64:unknown]')


title('TOALM 2', 'listmissing full in E1_list_missing_packages')
populate_local_temp('E1_list_missing_packages/')
obsoleta = ObsoletaApi(conf, args)

package = Package.construct_from_compact(conf, 'a')
error, missing = obsoleta.list_missing_full(package)
test_error(error, ErrorCode.RESOLVE_ERROR)
b_parent = missing['b:1.1.1:anytrack:c64:unknown']['parent']
test_eq(b_parent, 'a:1.1.1:anytrack:c64:unknown')
