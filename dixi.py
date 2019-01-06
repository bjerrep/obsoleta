#!/usr/bin/env python3
from log import logger as log
from common import ErrorCode, Setup
from version import Version
from package import Package
import json
import os
import logging
import datetime
import time
import argparse


class Packagefile:
    def __init__(self, package):
        self.package = package
        self.dict = package.to_dict()

    def dump(self):
        return json.dumps(self.dict, indent=4)

    def add_action(self, action):
        log.info(action)
        self.dict['dixi_action'] = action

    def version_digit_increase(self, position):
        version = Version(self.dict['version'])
        org_version = str(version)
        version.increase(position)
        self.dict['version'] = str(version)
        action = 'version increased from %s to %s' % (org_version, version)
        self.add_action(action)
        return ErrorCode.OK

    def save(self):
        with open(self.package.packagepath, 'w') as f:
            # Calculate the offset taking into account daylight saving time - https://stackoverflow.com/a/28147286
            utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
            utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
            now = datetime.datetime.now()
            local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
            self.dict['dixi_modified'] = local_with_tz

            f.write(self.dump())

    def set_track(self, track):
        org_track = self.dict.get('track')
        self.dict['track'] = track
        action = 'track from %s to %s' % (str(org_track), track)
        self.add_action(action)
        return ErrorCode.OK

    def set_arch(self, arch):
        org_arch = self.dict.get('arch')
        self.dict['arch'] = arch
        action = 'arch from %s to %s' % (str(org_arch), arch)
        self.add_action(action)
        return ErrorCode.OK

    def set_buildtype(self, buildtype):
        org_buildtype = self.dict.get('buildtype')
        self.dict['buildtype'] = buildtype
        action = 'track from %s to %s' % (str(org_buildtype), buildtype)
        self.add_action(action)
        return ErrorCode.OK


# ---------------------------------------------------------------------------------------------

def print_error(message):
    print(message)


def print_message(message):
    print(message)


parser = argparse.ArgumentParser('dixi')
parser.add_argument('--json', dest='packagepath',
                    help='the path for the package. See also --package')
parser.add_argument('--print', action='store_true',
                    help='command: pretty print the packagefile')
parser.add_argument('--inc_major', action='store_true',
                    help='command: increase the major with one')
parser.add_argument('--inc_minor', action='store_true',
                    help='command: increase the minor with one')
parser.add_argument('--inc_build', action='store_true',
                    help='command: increase the buildnumber with one')
parser.add_argument('--track',
                    help='command: set the track identifier')
parser.add_argument('--arch',
                    help='command: set the arch identifier')
parser.add_argument('--buildtype',
                    help='command: set the buildtype identifier')
parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--printtemplate', action='store_true',
                    help='print a blank obsoleta.json')

parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify the package file')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')

results = parser.parse_args()

if results.printtemplate:
    with open(os.path.join(Setup.obsoleta_root, 'obsoleta.json.template')) as f:
        print(f.read())
    exit(ErrorCode.OK.value)

if results.verbose:
    log.setLevel(logging.DEBUG)

Setup.load_configuration(results.conffile)

try:
    package = Package.construct_from_packagepath(results.packagepath)
except FileNotFoundError as e:
    print_error(str(e))
    exit(ErrorCode.PACKAGE_NOT_FOUND.value)

try:
    pf = Packagefile(package)
except FileNotFoundError as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

exit_code = ErrorCode.UNSET
save_pending = False

if results.inc_major:
    exit_code = pf.version_digit_increase(0)
    save_pending = True
elif results.inc_minor:
    exit_code = pf.version_digit_increase(1)
    save_pending = True
elif results.inc_build:
    exit_code = pf.version_digit_increase(2)
    save_pending = True
elif results.track:
    if not Setup.using_track:
        print_error('track identifier is not enabled, see --conf')
    exit_code = pf.set_track(results.track)
    save_pending = True
elif results.arch:
    if not Setup.using_arch:
        print_error('arch identifier is not enabled, see --conf')
    exit_code = pf.set_arch(results.arch)
    save_pending = True
elif results.buildtype:
    if not Setup.using_buildtype:
        print_error('buildtype identifier is not enabled, see --conf')
    exit_code = pf.set_buildtype(results.buildtype)
    save_pending = True
elif not results.print:
    print_error('no command found')

if save_pending:
    if results.dryrun:
        print_message('dry run, package file is not rewritten')
    else:
        pf.save()

if results.print:
    print_message(pf.dump())
    exit_code = ErrorCode.OK

exit(exit_code.value)
