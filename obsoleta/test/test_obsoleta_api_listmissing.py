#!/usr/bin/env python3
from obsoleta.test.test_common import TESTDATA_PATH, title, test_eq, test_error, populate_local_temp
from obsoleta.common import Conf
from obsoleta.errorcodes import ErrorCode
from obsoleta.obsoleta_api import Args, ObsoletaApi
from obsoleta.package import Package

args = Args()
args.set_depth(2)
args.set_root('local/temp')
# args.set_info_logging()
conf = Conf(f'{TESTDATA_PATH}/test.conf')

title('TOALM 1', 'listmissing in E1_list_missing_packages')
populate_local_temp('E1_list_missing_packages/')
obsoleta = ObsoletaApi(conf, args)

package = Package.construct_from_compact(conf, 'a')
error, missing = obsoleta.list_missing(package)
test_error(error, ErrorCode.RESOLVE_ERROR, missing)
test_eq('[b:1.1.1:anytrack:c64:unknown, e:1.1.1:anytrack:c64:unknown]', str(missing))
