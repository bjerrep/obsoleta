from log import deb, inf
from errorcodes import ErrorCode
from exceptions import BadPath
import os, json, time, datetime
from enum import Enum


class Position(Enum):
    MAJOR = 0
    MINOR = 1
    BUILD = 2


_setup = None


def get_setup():
    return _setup


class Setup:
    """
    The setup class represents the settings in the configuration
    file (default 'obsoleta.conf')
    """
    paths = []
    blacklist_paths = []
    using_track = False
    using_arch = False
    using_buildtype = False
    using_all_optionals = False
    allow_duplicates = True
    keepgoing = False
    cache = False
    obsoleta_root = None
    depth = 1
    semver = False
    relaxed_multislot = False       # allow a multislot key dir to be given as package root. Naughty,

    def __init__(self, configuration_file=None):
        global _setup
        _setup = self

        Setup.obsoleta_root = os.path.dirname(os.path.abspath(__file__))

        if configuration_file:
            conffile = configuration_file
        else:
            conffile = os.path.join(Setup.obsoleta_root, 'obsoleta.conf')

        try:
            with open(conffile) as f:
                conf = json.loads(f.read())
                try:
                    self.paths += conf.get('root')
                except:
                    pass
                env_paths = conf.get('env_root')
                if env_paths:
                    expanded = os.path.expandvars(env_paths)
                    deb('environment search path %s expanded to %s' % (env_paths, expanded))
                    self.paths += expanded.split(os.pathsep)
                blacklist_paths = conf.get('blacklist_paths')
                if blacklist_paths:
                    Setup.blacklist_paths = blacklist_paths
                self.using_arch = conf.get('using_arch')
                self.using_track = conf.get('using_track')
                self.using_buildtype = conf.get('using_buildtype')
                if self.using_arch and self.using_track and self.using_buildtype:
                    self.using_all_optionals = True
                self.allow_duplicates = conf.get('allow_duplicates')
                self.keepgoing = conf.get('keepgoing')
                self.cache = conf.get('cache')
                self.semver = conf.get('semver')
                self.relaxed_multislot = conf.get('relaxed_multislot')
                self.relative_trace_paths = conf.get('relative_trace_paths')
                try:
                    self.depth = int(conf['depth'])
                except KeyError:
                    pass
        except FileNotFoundError:
            inf('no configuration file %s found - continuing regardless' % conffile)

    def dump(self):
        deb('Configuration:')
        deb('  depth = %i' % self.depth)


class Args:
    """
    The args class represents some of the parameters typically comming from
    the commandline (added ad-hoc)
    """
    depth = None
    root = ''
    verbose = False
    info = False
    keypath = None
    skip_bumping_ranged_versions = False

    def set_depth(self, depth):
        self.depth = depth

    def set_root(self, root):
        self.root = root

    def set_slot_path(self, keypath):
        self.keypath = keypath

    def set_skip_bumping_ranged_versions(self, skip_bumping_ranged_versions):
        self.skip_bumping_ranged_versions = skip_bumping_ranged_versions


class Error:
    def __init__(self, errorcode, package, message=''):
        self.errorcode = errorcode
        self.package = package
        if message:
            self.message = message
        elif package and package.parent:
            self.message = 'from parent ' + package.parent.to_string()
        else:
            self.message = ''

    def get_errorcode(self):
        return self.errorcode

    def has_error(self):
        return self.errorcode != ErrorCode.OK

    def is_ok(self):
        return self.errorcode == ErrorCode.OK

    def __str__(self):
        if not self.package:
            return ErrorCode.to_string(self.errorcode.value)
        return ErrorCode.to_string(self.errorcode.value) + ': ' + self.package.to_string()

    def to_string(self):
        return ErrorCode.to_string(self.errorcode.value) + ': ' + self.package.to_string() + ' ' + str(self.message)

    def get_message(self):
        return self.message

    def print(self):
        if self.message:
            return '%s, %s' % (ErrorCode.to_string(self.errorcode.value), self.message)
        try:
            return '%s, %s' % (ErrorCode.to_string(self.errorcode.value), self.package.to_string())
        except:
            return '%s' % ErrorCode.to_string(self.errorcode.value)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __lt__(self, other):
        if self.errorcode.value < other.errorcode.value:
            return True
        if self.message < other.message:
            return True
        return self.package.to_string() < other.package.to_string()

    def __hash__(self):
        uid = str(self)
        return hash(uid)


class ErrorOk(Error):
    def __init__(self):
        super(ErrorOk, self).__init__(ErrorCode.OK, None)


def find_in_path(path, filename, maxdepth, results, dirs_checked=1):
    try:
        scan_list = list(os.scandir(path))
    except FileNotFoundError:
        raise BadPath('bad path %s' % path)

    for entry in scan_list:
        if entry.name == 'obsoleta.skip':
            deb('- skip file found, ignoring %s recursively' % entry.path)
            return dirs_checked

    for entry in scan_list:
        if entry.is_dir():
            is_blacklisted = False
            for blacklist in Setup.blacklist_paths:
                if blacklist in os.path.join(path, entry.name):
                    deb('- blacklisted, ignoring %s recursively' % entry.path)
                    is_blacklisted = True

            if is_blacklisted:
                continue

            if maxdepth:
                maxdepth -= 1
                dirs_checked += 1
                find_in_path(entry.path, filename, maxdepth, results, dirs_checked)
                maxdepth += 1

        if entry.name == filename:
            results.append(entry.path)
            deb('located %s' % printing_path(entry.path))

    return dirs_checked


def get_package_filepath(path):
    if path.endswith('obsoleta.json'):
        return path
    return os.path.join(path, 'obsoleta.json')


def get_key_filepath(path):
    if path.endswith('obsoleta.key'):
        return path
    return os.path.join(path, 'obsoleta.key')


def printing_path(path):
    """
    Return an absolute path as relative to Setup.root. Enable in setup file as
    'relative_trace_paths' if the full paths in trace output are just a complete
    waste of space and are distracting to look at.
    """
    try:
        if _setup.relative_trace_paths:
            return path.replace(_setup.root, '')[1:]
    except:
        pass
    return path


def get_local_time_tz():
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    now = datetime.datetime.now()
    local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
    return local_with_tz
