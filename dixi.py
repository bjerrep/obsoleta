#!/usr/bin/env python3
from log import logger as log
from log import inf, err, cri
from common import ErrorCode, Setup, Exceptio
from common import get_package_filepath, get_key_filepath
from version import Version
from package import Layout, Package
import json, os, logging, datetime, time, argparse


class Packagefile:
    def __init__(self, package):
        self.package = package
        self.dict = self.package.to_dict()
        self.unmodified_dict = self.package.to_unmodified_dict()
        self.action = ''
        self.new_version = False
        self.new_track = False

    def dump(self):
        return json.dumps(self.dict, indent=2)

    def get_package(self):
        return self.package

    def add_action(self, action):
        log.info(action)
        self.action = action

    def getter(self, key):
        if self.package.layout == Layout.standard:
            return '', self.unmodified_dict[key]

        try:
            return self.package.key, self.unmodified_dict[self.package.key][key]
        except:
            try:
                return 'slot', self.unmodified_dict['slot'][key]
            except:
                return 'multislot', self.unmodified_dict['multislot'][key]

    def setter(self, section, key, value):
        if not section:
            self.unmodified_dict[key] = value
        else:
            self.unmodified_dict[section][key] = value

    def set_version(self, version):
        section, ver = self.getter('version')
        org_version = str(Version(ver))
        self.setter(section, 'version', version)
        action = 'version increased from %s to %s' % (org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return str(version)

    def version_digit_increment(self, position):
        section, ver = self.getter('version')
        version = Version(ver)
        org_version = str(version)
        version.increase(position)
        self.setter(section, 'version', str(version))
        action = 'version increased from %s to %s' % (org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return str(version)

    def save(self):
        package_file = os.path.join(self.package.package_path, 'obsoleta.json')

        with open(package_file, 'w') as f:
            utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
            utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
            now = datetime.datetime.now()
            local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
            self.unmodified_dict['dixi_modified'] = local_with_tz
            self.unmodified_dict['dixi_action'] = self.action
            f.write(json.dumps(self.unmodified_dict, indent=2))

    def set_track(self, track):
        section, org_track = self.getter('track')
        self.setter(section, 'track', track)
        action = 'track from %s to %s' % (org_track, track)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return track

    def get_track(self):
        _, track = self.getter('track')
        return track

    def set_arch(self, arch):
        section, org_arch = self.getter('arch')
        self.setter(section, 'arch', arch)
        action = 'arch from %s to %s' % (org_arch, arch)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return arch

    def get_arch(self):
        _, arch = self.getter('arch')
        return arch

    def set_buildtype(self, buildtype):
        section, org_buildtype = self.getter('buildtype')
        self.setter(section, 'buildtype', buildtype)
        action = 'buildtype from %s to %s' % (org_buildtype, buildtype)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return buildtype

    def get_buildtype(self):
        _, buildtype = self.getter('buildtype')
        return buildtype

# ---------------------------------------------------------------------------------------------


parser = argparse.ArgumentParser('dixi', description='''
    dixi is used for inquiring and modifying a specific package file with the intention
    that it should rarely be necessary to edit a package file directly.
    ''')
parser.add_argument('--path',
                    help='the path for the package to work on')
parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')

parser.add_argument('--print', action='store_true',
                    help='command: pretty print the packagefile')
parser.add_argument('--printtemplate', action='store_true',
                    help='print a blank obsoleta.json')
parser.add_argument('--printkey', metavar='key:value',
                    help='print a obsoleta.key on stdout. Argument value is the (multi)slot name')

parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify the package file')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')
parser.add_argument('--newline', action='store_true',
                    help='the getters default runs without trailing newlines, this one adds them back in')
parser.add_argument('--keypath',
                    help='the relative keypath (directory name) to use for a multislotted package')

parser.add_argument('--getname', action='store_true',
                    help='command: get name')
parser.add_argument('--getcompact', action='store_true',
                    help='command: get compact name')

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
    _package = Package.construct_from_compact('a:0.0.0:development:archname:buildtype')
    _depends = Package.construct_from_compact('b:0.0.0:development:archname:buildtype')
    _package.add_dependency(_depends)
    package_file = Packagefile(_package)
    print(package_file.dump())
    exit(ErrorCode.OK.value)

if results.printkey:
    key, value = results.printkey.split(':')
    _json = {key: value}
    print(json.dumps(_json, indent=4))
    exit(ErrorCode.OK.value)

if not results.path:
    cri('need a path to the package to work with, see --path', ErrorCode.MISSING_INPUT)

if results.verbose:
    log.setLevel(logging.DEBUG)

Setup.load_configuration(results.conffile)

try:
    package_path = get_package_filepath(results.path)
    if Package.is_multislot(package_path):
        if not results.keypath:
            cri('the key directory to use is required for a multislot package', ErrorCode.MULTISLOT_ERROR)
        key_file = os.path.join(results.path, get_key_filepath(results.keypath))
        package = Package.construct_from_multislot_package_path(results.path, key_file)
    else:
        package = Package.construct_from_package_path(results.path)

except Exceptio as e:
    log.critical(str(e))
    exit(e.ErrorCode.value)
except Exception as e:
    err(str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)

try:
    pf = Packagefile(package)
except FileNotFoundError as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

save_pending = False
ret = None

if results.getname:
    ret = pf.get_package().get_name()

elif results.getcompact:
    ret = pf.get_package().to_string()

elif results.getversion:
    ret = pf.get_package().get_version()

elif results.setversion:
    ret = pf.set_version(results.setversion)
    save_pending = True

elif results.incmajor:
    ret = pf.version_digit_increment(0)
    save_pending = True

elif results.incminor:
    ret = pf.version_digit_increment(1)
    save_pending = True

elif results.incbuild:
    ret = pf.version_digit_increment(2)
    save_pending = True

elif results.settrack:
    if not Setup.using_track:
        err('track identifier is not enabled, see --conf')
    ret = pf.set_track(results.settrack)
    save_pending = True

elif results.gettrack:
    if not Setup.using_track:
        err('track identifier is not enabled, see --conf')
    ret = pf.get_track()

elif results.setarch:
    if not Setup.using_arch:
        err('arch identifier is not enabled, see --conf')
    ret = pf.set_arch(results.setarch)
    save_pending = True

elif results.getarch:
    if not Setup.using_arch:
        err('arch identifier is not enabled, see --conf')
    ret = pf.get_arch()

elif results.setbuildtype:
    if not Setup.using_buildtype:
        err('buildtype identifier is not enabled, see --conf')
    ret = pf.set_buildtype(results.setbuildtype)
    save_pending = True

elif results.getbuildtype:
    if not Setup.using_buildtype:
        err('buildtype identifier is not enabled, see --conf')
    ret = pf.get_buildtype()

elif results.print:
    inf(pf.dump())

else:
    err('no command found')
    exit(ErrorCode.MISSING_INPUT.value)

if ret:
    inf(str(ret), results.newline)

if save_pending:
    if results.dryrun:
        inf('dry run, package file is not rewritten')
    else:
        pf.save()


exit(ErrorCode.OK.value)
