import os, json, time, datetime
from enum import Enum
from log import set_log_level, deb
from errorcodes import ErrorCode
from exceptions import BadPath


class Position(Enum):
    MAJOR = 0
    MINOR = 1
    BUILD = 2


_conf = None


def get_conf():
    return _conf


class Conf:
    """
    The Conf class represents the settings in the configuration
    file (default 'obsoleta.conf')
    """
    def __init__(self, configuration_file=None):
        global _conf

        self.paths = []
        self.blacklist_paths = []
        self.using_track = False
        self.using_arch = False
        self.using_buildtype = False
        self.using_all_optionals = False
        self.allow_duplicates = False
        self.keepgoing = False
        self.cache = False
        self.depth = 1
        self.semver = False
        # allow a multislot key dir to be given as package root. Naughty,
        self.relaxed_multislot = False
        self.keep_track = False
        # Register a multislot package according to the slots it lists in the package file.
        # The alternative is that only the slots for which a physical keyfile is found is parsed.
        self.parse_multislot_directly = True

        _conf = self

        self.obsoleta_root = os.path.dirname(os.path.abspath(__file__))

        if configuration_file == 'default':
            return

        if configuration_file:
            conf_file = configuration_file
        else:
            conf_file = os.path.join(self.obsoleta_root, 'obsoleta.conf')

        try:
            with open(conf_file) as f:
                conf = json.loads(f.read())
                try:
                    conf_root = conf.get('root')
                    for cr in conf_root:
                        if cr:
                            self.paths.append(cr)
                except:
                    pass
                env_paths = conf.get('env_root')
                if env_paths:
                    expanded = os.path.expandvars(env_paths)
                    deb(f'environment search path {env_paths} expanded to {expanded}')
                    self.paths += expanded.split(os.pathsep)
                blacklist_paths = conf.get('blacklist_paths')
                if blacklist_paths:
                    self.blacklist_paths = blacklist_paths
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
                self.keep_track = conf.get('keep_track')
                self.relative_trace_paths = conf.get('relative_trace_paths')
                if conf.get('parse_multislot_directly') is not None:
                    self.parse_multislot_directly = conf.get('parse_multislot_directly')
                try:
                    self.depth = int(conf['depth'])
                except KeyError:
                    pass
        except FileNotFoundError:
            raise Exception(f'configuration file "{conf_file}" not found')

    def dump(self):
        deb('Configuration:')
        deb(f'  depth = {self.depth}')


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
    set_log_level()

    def set_verbose_logging(self):
        self.verbose = True
        self.info = False
        set_log_level(verbose=True)

    def set_info_logging(self):
        self.verbose = False
        self.info = True
        set_log_level(info=True)

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

    def get_package(self):
        return self.package

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
        if self.message:
            return self.message
        return self.to_string()

    def print(self):
        if self.message:
            try:
                package_string = self.package.to_string()
            except:
                package_string = ''
            return '%s %s, %s' % (ErrorCode.to_string(self.errorcode.value), package_string, self.message)
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
            for blacklist in _conf.blacklist_paths:
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
    Return an absolute path as relative to Conf.root. Enable in configuration file as
    'relative_trace_paths' if the full paths in trace output are just a complete
    waste of space and are distracting to look at.
    """
    try:
        if _conf.relative_trace_paths:
            return path.replace(_conf.paths[0], '')
    except:
        pass
    return path


def get_local_time_tz():
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    now = datetime.datetime.now()
    local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
    return local_with_tz


def pretty(dictionary):
    return json.dumps(dictionary, indent=2)
