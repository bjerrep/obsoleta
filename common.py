from log import logger as log
from enum import Enum
import os
import json


class IllegalPackage(Exception):
    pass


class NoPackage(Exception):
    pass


def print_error(message):
    print(message)


def print_message(message):
    print(message)


class Setup:
    paths = []
    blacklist_paths = []
    using_track = False
    using_arch = False
    using_buildtype = False
    allow_duplicates = False
    indent = ''
    obsoleta_root = None
    max_depth = 1

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
                paths += conf.get('paths')
                env_paths = conf.get('env_paths')
                if env_paths:
                    expanded = os.path.expandvars(env_paths)
                    log.info('environment search path %s expanded to %s' % (env_paths, expanded))
                    paths += expanded.split(os.pathsep)
                Setup.paths = paths
                blacklist_paths = conf.get('blacklist_paths')
                if blacklist_paths:
                    Setup.blacklist_paths = blacklist_paths
                Setup.using_arch = conf.get('using_arch') == 'on'
                Setup.using_track = conf.get('using_track') == 'on'
                Setup.using_buildtype = conf.get('using_buildtype') == 'on'
                Setup.allow_duplicates = conf.get('allow_duplicates') == 'yes'
                try:
                    Setup.max_depth = int(conf['max_depth'])
                except KeyError:
                    pass
        except FileNotFoundError:
            log.info('no configuration file %s found - continuing regardless' % conffile)
        return paths


class Indent():
    def __init__(self):
        Setup.indent += '  '

    def __del__(self):
        Setup.indent = Setup.indent[:-3]


class ErrorCode(Enum):
    OK = 0
    UNSET = 1
    DEPENDENCY_NOT_FOUND = 2
    PACKAGE_NOT_FOUND = 3
    ARCH_MISMATCH = 4
    MULTIPLE_VERSIONS = 5
    CIRCULAR_DEPENDENCY = 6
    TEST_FAILED = 7
    SYNTAX_ERROR = 8
    MISSING_INPUT = 9
    BAD_PATH = 10

    @staticmethod
    def to_string(errorcode):
        ErrorCodeToString = \
           ['Ok',
            'Unset',
            'Dependency not found',
            'Package not found',
            'Mixing different arch',
            'Multiple versions',
            'Circular dependency',
            'Test failed',
            'Syntax error',
            'Missing input',
            'Bad path']

        return ErrorCodeToString[errorcode]


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
