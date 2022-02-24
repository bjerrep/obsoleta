#!/usr/bin/env python3
from test_common import title, test_true
from common import Conf
import package
import exceptions


conf = Conf('testdata/test.conf')


title('TPACKAGE 1A', 'multislot with invalid key')
try:
    _package = package.Package.construct_from_package_path(
        conf,
        'testdata/G4_test_multislot_bad_key',
        'bad_key')
    test_true(False)
except exceptions.InvalidKeyFile as e:
    print(str(e))
except:
    test_true(False)
