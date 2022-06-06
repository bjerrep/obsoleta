#!/usr/bin/env python3
import os
from .test_common import title, test_true, test_eq
from obsoleta.common import Conf
import obsoleta.package as package
import obsoleta.exceptions

test_data = f'{os.path.dirname(__file__)}/testdata'

conf = Conf(f'{test_data}/test.conf')


title('TPACKAGE 1A', 'multislot with invalid key')
try:
    _package = package.Package.construct_from_package_path(
        conf,
        f'{test_data}/G4_test_multislot_bad_key',
        'bad_key')
    test_true(False)
except obsoleta.exceptions.InvalidKeyFile as e:
    print(str(e))
except:
    test_true(False)


title('TPACKAGE 1B', 'packages can be sorted')
package1 = package.Package.construct_from_compact(conf, "a:2.0.1")
package2 = package.Package.construct_from_compact(conf, "a:2.0.2")
package0 = package.Package.construct_from_compact(conf, "a:2.0.0")
package_list = [package1, package2, package0]

sorted_list = sorted(package_list)
expected_list = [package0, package1, package2]
test_eq(expected_list, sorted_list)

sorted_list = sorted(package_list, reverse=True)
expected_list = [package2, package1, package0]
test_eq(expected_list, sorted_list)
