from log import deb, inf
from errorcodes import ErrorCode
import os
import json


class IllegalPackage(Exception):
    pass


class NoPackage(Exception):
    pass


class InvalidPackage(Exception):
    pass


class IllegalKey(Exception):
    pass


class MissingKeyFile(Exception):
    pass


class InvalidKeyFile(Exception):
    pass


def print_error(message):
    print(message)


def print_message(message):
    print(message)


def print_value(message, add_newline=True):
    print(message, end='\n' if add_newline else '')


class Setup:
    paths = []
    blacklist_paths = []
    using_track = False
    using_arch = False
    using_buildtype = False
    ignore_duplicates = False
    obsoleta_root = None
    depth = 1

    @staticmethod
    def load_configuration(configuration_file=None):
        Setup.obsoleta_root = os.path.dirname(os.path.abspath(__file__))
        paths = []
        conffile = os.path.join(Setup.obsoleta_root, 'obsoleta.conf')
        if configuration_file:
            conffile = configuration_file
            if not os.path.exists(conffile):
                print_error('no configuration file "%s" found' % conffile)
                exit(ErrorCode.MISSING_INPUT.value)

        try:
            with open(conffile) as f:
                conf = json.loads(f.read())
                try:
                    paths += conf.get('root')
                except:
                    pass
                env_paths = conf.get('env_root')
                if env_paths:
                    expanded = os.path.expandvars(env_paths)
                    inf('environment search path %s expanded to %s' % (env_paths, expanded))
                    paths += expanded.split(os.pathsep)
                Setup.paths = paths
                blacklist_paths = conf.get('blacklist_paths')
                if blacklist_paths:
                    Setup.blacklist_paths = blacklist_paths
                Setup.using_arch = conf.get('using_arch') == 'on'
                Setup.using_track = conf.get('using_track') == 'on'
                Setup.using_buildtype = conf.get('using_buildtype') == 'on'
                Setup.ignore_duplicates = conf.get('allow_duplicates') == 'yes'
                try:
                    Setup.depth = int(conf['depth'])
                except KeyError:
                    pass
        except FileNotFoundError:
            inf('no configuration file %s found - continuing regardless' % conffile)
        return paths

    @staticmethod
    def dump():
        deb('Configuration:')
        deb('  depth = %i' % Setup.depth)


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
    scan_list = list(os.scandir(path))

    for entry in scan_list:
        if entry.name == 'obsoleta.skip':
            inf('- skip file found, ignoring %s recursively' % entry.path)
            return dirs_checked

    for entry in scan_list:
        if entry.is_dir():
            is_blacklisted = False
            for blacklist in Setup.blacklist_paths:
                if blacklist in os.path.join(path, entry.name):
                    inf('- blacklisted, ignoring %s recursively' % entry.path)
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
            inf('- found %s' % entry.path)
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
