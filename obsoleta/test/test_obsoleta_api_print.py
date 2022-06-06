#!/usr/bin/env python3
import json
from obsoleta.test.test_common import TESTDATA_PATH, title, test_ok, test_eq, populate_local_temp
from obsoleta.common import Conf
from obsoleta.obsoleta_api import Args, ObsoletaApi
from obsoleta.package import Package

args = Args()
args.set_depth(2)
args.set_root('local/temp')
# args.set_info_logging()
conf = Conf(f'{TESTDATA_PATH}/test.conf')

title('TOAP 1', 'print a from G2_test_slot')
populate_local_temp('G2_test_slot')
obsoleta = ObsoletaApi(conf, args)

package = Package.construct_from_compact(conf, 'a')
error, manifest = obsoleta.print(package)
test_ok(error)
test_eq(json.dumps(manifest),
        '{"name": "a", "version": "1.1.1", "arch": "linux", "depends": [{"name": "b", "version": "2.2.2"},'
        ' {"name": "c", "version": "3.3.3"}, {"name": "d", "version": "4.4.4", "arch": "linux"}, '
        '{"name": "f", "version": "6.6.6", "arch": "linux"}, {"name": "e", "version": "5.5.5", "arch": "linux"}]}')


title('TOAP 2', 'print a from G1_test_multislot')
populate_local_temp('G1_test_multislot')
obsoleta = ObsoletaApi(conf, args)
package = Package.construct_from_compact(conf, 'a')
error, manifest = obsoleta.print(package)
test_ok(error)
test_eq(json.dumps(manifest),
        '{"name": "a", "version": "0.0.0", "arch": "windows", "depends": [{"name": "c", "version": "2.2.2", "arch": "windows"}, '
        '{"name": "w", "version": "88.88.88", "about": "e.g. a small toolchain asset that should not unconditionally trigger changes in the gigantic downstream b asset, see b"}, '
        '{"name": "x", "version": "3.2.1", "arch": "anyarch"}, {"name": "y", "version": "8.8.8", "arch": "windows"}, '
        '{"name": "z", "version": "99.99.99", "arch": "anyarch", "about": "e.g. a small toolchain asset that should not unconditionally trigger changes in the gigantic downstream b asset, see b"}, '
        '{"name": "b", "version": "1.1.1", "arch": "windows"}]}')
