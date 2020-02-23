from log import deb, inf
from errorcodes import ErrorCode
import os
import json


class Exceptio(Exception):
    def __init__(self, msg, ErrorCode):
        super().__init__(msg)
        self.ErrorCode = ErrorCode


class Setup:
    paths = []
    blacklist_paths = []
    using_track = False
    using_arch = False
    using_buildtype = False
    ignore_duplicates = False
    keepgoing = False
    cache = False
    obsoleta_root = None
    depth = 1

    def __init__(self, configuration_file=None):
        Setup.obsoleta_root = os.path.dirname(os.path.abspath(__file__))
        conffile = os.path.join(Setup.obsoleta_root, 'obsoleta.conf')
        if configuration_file:
            conffile = configuration_file
            if not os.path.exists(conffile):
                raise Exceptio('no configuration file "%s" found' % conffile, ErrorCode.MISSING_INPUT)

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
                self.using_arch = conf.get('using_arch') == 'on'
                self.using_track = conf.get('using_track') == 'on'
                self.using_buildtype = conf.get('using_buildtype') == 'on'
                self.ignore_duplicates = conf.get('allow_duplicates') == 'yes'
                self.keepgoing = conf.get('keepgoing') == 'true'
                self.cache = conf.get('cache') == 'on'
                try:
                    self.depth = int(conf['depth'])
                except KeyError:
                    pass
        except FileNotFoundError:
            inf('no configuration file %s found - continuing regardless' % conffile)

    def dump(self):
        deb('Configuration:')
        deb('  depth = %i' % self.depth)


class Param:
    depth = None
    root = ''

    def set_depth(self, depth):
        self.depth = depth

    def set_root(self, root):
        self.root = root


class Error:
    def __init__(self, error_type, package, message=''):
        self.error_type = error_type
        self.package = package
        if message:
            self.message = message
        elif package.parent:
            self.message = 'from parent ' + package.parent.to_string()
        else:
            self.message = ''

    def get_error(self):
        return self.error_type

    def __str__(self):
        return ErrorCode.to_string(self.error_type.value) + ': ' + self.package.to_string()

    def to_string(self):
        return ErrorCode.to_string(self.error_type.value) + ': ' + self.package.to_string() + ' ' + str(self.message)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        uid = str(self)
        return hash(uid)


def find_in_path(path, filename, maxdepth, results, dirs_checked=1):
    try:
        scan_list = list(os.scandir(path))
    except FileNotFoundError:
        raise Exceptio('bad path %s' % path, ErrorCode.BAD_PATH)

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
            deb('- found %s' % entry.path)
            continue
    return dirs_checked


def get_package_filepath(path):
    if path.endswith('obsoleta.json'):
        return path
    return os.path.join(path, 'obsoleta.json')


def get_key_filepath(path):
    if path.endswith('obsoleta.key'):
        return path
    return os.path.join(path, 'obsoleta.key')
