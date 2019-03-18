#!/usr/bin/env python3
from log import logger as log
from common import ErrorCode, Setup, IllegalPackage, print_message, print_value, print_error
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
        self.action = ''
        self.new_version = False
        self.new_track = False

    def dump(self, _dict=None):
        if not _dict:
            _dict = self.dict
        return json.dumps(_dict, indent=4)

    def get_package(self):
        return self.package

    def add_action(self, action):
        log.info(action)
        self.action = action

    def set_version(self, version):
        org_version = str(Version(self.dict['version']))
        self.dict['version'] = version
        action = 'version increased from %s to %s' % (org_version, version)
        self.add_action(action)
        self.new_version = True
        return str(version)

    def version_digit_increase(self, position):
        version = Version(self.dict['version'])
        org_version = str(version)
        version.increase(position)
        self.dict['version'] = str(version)
        action = 'version increased from %s to %s' % (org_version, version)
        self.add_action(action)
        self.new_version = True
        return str(version)

    def save(self):
        package_file = os.path.join(self.package.package_path, 'obsoleta.json')

        if self.package.get_key():
            with open(package_file) as f:
                _dict = json.loads(f.read())
                if self.new_version:
                    _dict['base']['version'] = self.dict['version']
                elif self.new_track:
                    _dict['base']['track'] = self.dict['track']
                else:
                    print_error('can only rewrite version and track in slotted package file, sorry...')
                    exit(ErrorCode.SLOT_ERROR.value)
        else:
            _dict = self.dict

        with open(package_file, 'w') as f:
            # Add the modification time with the key 'dixi_modified'.
            # Calculate the offset taking into account daylight saving time - https://stackoverflow.com/a/28147286
            utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
            utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
            now = datetime.datetime.now()
            local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
            _dict['dixi_modified'] = local_with_tz
            _dict['dixi_action'] = self.action
            f.write(self.dump(_dict))

    def set_track(self, track):
        org_track = self.dict.get('track')
        self.dict['track'] = track
        action = 'track from %s to %s' % (str(org_track), track)
        self.add_action(action)
        self.new_track = True
        return track

    def get_track(self):
        return self.dict.get('track')

    def set_arch(self, arch):
        org_arch = self.dict.get('arch')
        self.dict['arch'] = arch
        action = 'arch from %s to %s' % (str(org_arch), arch)
        self.add_action(action)
        return arch

    def get_arch(self):
        return self.dict.get('arch')

    def set_buildtype(self, buildtype):
        org_buildtype = self.dict.get('buildtype')
        self.dict['buildtype'] = buildtype
        action = 'track from %s to %s' % (str(org_buildtype), buildtype)
        self.add_action(action)
        return buildtype

    def get_buildtype(self):
        return self.dict.get('buildtype')

# ---------------------------------------------------------------------------------------------


parser = argparse.ArgumentParser('dixi', description='''
    dixi is used for inquiring and modifying a specific package file.
    Note that only version and track are supported for slotted package files, and that the changes
    will be always be written in the base section. The key sections will never be modified even if a version
    or track originally came from one of these.
    ''')
parser.add_argument('--path', required=True,
                    help='the path for the package. See also --package')
parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')

parser.add_argument('--print', action='store_true',
                    help='command: pretty print the packagefile')
parser.add_argument('--printtemplate', action='store_true',
                    help='print a blank obsoleta.json')
parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify the package file')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')
parser.add_argument('--newline', action='store_true',
                    help='the getters default runs without trailing newlines, this one adds them back in')

parser.add_argument('--getversion', action='store_true',
                    help='command: get version')
parser.add_argument('--setversion',
                    help='command: set the version to SETVERSION')

parser.add_argument('--incmajor', action='store_true',
                    help='command: increase the major with one')
parser.add_argument('--incminor', action='store_true',
                    help='command: increase the minor with one')
parser.add_argument('--incbuild', action='store_true',
                    help='command: increase the buildnumber with one')

parser.add_argument('--settrack',
                    help='command: set track')
parser.add_argument('--gettrack', action='store_true',
                    help='command: get track')

parser.add_argument('--setarch',
                    help='command: set arch')
parser.add_argument('--getarch', action='store_true',
                    help='command: get arch')

parser.add_argument('--setbuildtype',
                    help='command: set buildtype (e.g. release, debug)')
parser.add_argument('--getbuildtype', action='store_true',
                    help='command: get buildtype (e.g. release, debug)')

results = parser.parse_args()

if results.printtemplate:
    Setup.using_arch = True
    Setup.using_buildtype = True
    Setup.using_track = True
    _package = Package.construct_from_compact('a:development:archname:buildtype:0.0.0')
    _depends = Package.construct_from_compact('b:development:archname:buildtype:0.0.0')
    _package.add_dependency(_depends)
    package_file = Packagefile(_package)
    print(package_file.dump())
    exit(ErrorCode.OK.value)

if results.verbose:
    log.setLevel(logging.DEBUG)

Setup.load_configuration(results.conffile)

try:
    package = Package.construct_from_package_path(results.path)
except FileNotFoundError as e:
    print_error(str(e))
    exit(ErrorCode.PACKAGE_NOT_FOUND.value)
except IllegalPackage as e:
    print_error(str(e))
    exit(ErrorCode.PACKAGE_NOT_FOUND.value)
except json.JSONDecodeError as e:
    print_error('json error in package file: ' + str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)
except Exception as e:
    print_error(str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)
try:
    pf = Packagefile(package)
except FileNotFoundError as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

save_pending = False
ret = None

if results.getversion:
    ret = pf.get_package().get_version()

elif results.setversion:
    ret = pf.set_version(results.setversion)
    save_pending = True

elif results.incmajor:
    ret = pf.version_digit_increase(0)
    save_pending = True

elif results.incminor:
    ret = pf.version_digit_increase(1)
    save_pending = True

elif results.incbuild:
    ret = pf.version_digit_increase(2)
    save_pending = True

elif results.settrack:
    if not Setup.using_track:
        print_error('track identifier is not enabled, see --conf')
    ret = pf.set_track(results.settrack)
    save_pending = True

elif results.gettrack:
    if not Setup.using_track:
        print_error('track identifier is not enabled, see --conf')
    ret = pf.get_track()

elif results.setarch:
    if not Setup.using_arch:
        print_error('arch identifier is not enabled, see --conf')
    ret = pf.set_arch(results.setarch)
    save_pending = True

elif results.getarch:
    if not Setup.using_arch:
        print_error('arch identifier is not enabled, see --conf')
    ret = pf.get_arch()

elif results.setbuildtype:
    if not Setup.using_buildtype:
        print_error('buildtype identifier is not enabled, see --conf')
    ret = pf.set_buildtype(results.setbuildtype)
    save_pending = True

elif results.getbuildtype:
    if not Setup.using_buildtype:
        print_error('buildtype identifier is not enabled, see --conf')
    ret = pf.get_buildtype()

elif not results.print:
    print_error('no command found')

if ret:
    print_value(ret, results.newline)

if save_pending:
    if results.dryrun:
        print_message('dry run, package file is not rewritten')
    else:
        pf.save()

if results.print:
    print_message(pf.dump())


exit(ErrorCode.OK.value)
