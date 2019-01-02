#!/usr/bin/env python3
from log import logger as log
import json
import logging
import os
import argparse
from common import ErrorCode
from version import Version


class Packagefile:
    def __init__(self, file):
        if not file.endswith('obsoleta.json'):
            file = os.path.join(file, 'obsoleta.json')
        log.info('parsing file %s' % file)
        with open(file) as f:
            self.dict = json.loads(f.read())

    def dump(self):
        print(json.dumps(self.dict, indent=4))
        return ErrorCode.OK

    def version_digit_increase(self, position):
        version = Version(self.dict['version'])
        version.increase(position)
        self.dict['version'] = str(version)
        return ErrorCode.OK

# ---------------------------------------------------------------------------------------------

def print_error(message):
    print(message)


def print_message(message):
    print(message)


parser = argparse.ArgumentParser('dixi')
parser.add_argument('--package', dest='package', required=True,
                    help='the full path to a obsoleta.conf')
parser.add_argument('--print', action='store_true',
                    help='pretty print the packagefile and exit')
parser.add_argument('--inc_build', action='store_true',
                    help='increase the buildnumber with one')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')

results = parser.parse_args()

if results.verbose:
    log.setLevel(logging.DEBUG)

try:
    pf = Packagefile(results.package)
except FileNotFoundError as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

exit_code = ErrorCode.UNSET

if results.print:
    exit_code = pf.dump()
elif results.inc_build:
    exit_code = pf.version_digit_increase(2)
    pf.dump()
else:
    print_error('no command found')

exit(exit_code.value)



