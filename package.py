from log import logger as log
from log import Indent as Indent
from log import deb, war
from version import Version
from common import Setup, Error, Exceptio
from common import get_package_filepath, get_key_filepath
from errorcodes import ErrorCode
import json
import os
from enum import Enum
import copy


buildtype_unknown = 'unknown'
anyarch = 'anyarch'


class Track(Enum):
    defective = 0
    discontinued = 1
    anytrack = 2
    development = 3
    testing = 4
    production = 5

    def __ge__(self, other):
        return self.value >= other.value


TrackToString = ['defective', 'discontinued', 'anytrack', 'development', 'testing', 'production']


class Layout(Enum):
    standard = 0
    slot = 1
    multislot = 2


class Package:
    def __init__(self, package_path, compact, dictionary, key_file=None):
        self.parent = None
        self.package_path = package_path
        self.dependencies = None
        self.direct_dependency = True
        self.errors = None
        self.key = None
        self.unmodified_dict = None
        self.layout = Layout.standard

        if key_file:
            self.from_multislot_package_path(package_path, key_file)
        elif package_path:
            self.from_package_path(package_path)
        elif compact:
            self.from_compact(compact)
        else:
            self.from_dict(dictionary)

    @classmethod
    def construct_from_dict(cls, dictionary):
        return cls(None, None, dictionary)

    @classmethod
    def construct_from_package_path(cls, package_path):
        return cls(package_path, None, None)

    @classmethod
    def construct_from_multislot_package_path(cls, package_path, key_file):
        return cls(package_path, None, None, key_file)

    @classmethod
    def construct_from_compact(cls, compact):
        return cls(None, compact, None)

    def from_dict(self, dictionary):
        if not self.unmodified_dict:
            self.unmodified_dict = dictionary

        path = 'in ' + get_package_filepath(self.package_path) if self.package_path else ''
        try:
            self.name = dictionary['name']
        except:
            raise Exceptio('unable to extract name %s (sure its a json list?)' % path, ErrorCode.BAD_PACKAGE_FILE)
        try:
            self.version = Version(dictionary['version'])
        except:
            raise Exceptio('invalid version number %s' % path, ErrorCode.BAD_PACKAGE_FILE)

        # track, arch and buildtype are deliberately left undefined if they are disabled
        pedantic = True
        if Setup.using_track:
            if 'track' in dictionary:
                try:
                    self.track = Track[dictionary['track']]
                except KeyError:
                    raise Exceptio('invalid track name "%s" %s' %
                                   (dictionary['track'], path), ErrorCode.COMPACT_PARSE_ERROR)
            else:
                self.track = Track.anytrack
        elif pedantic and 'track' in dictionary:
            war('package %s specifies a track which is not enabled in config' % self.name)

        if Setup.using_arch:
            try:
                self.arch = dictionary["arch"]
            except:
                self.arch = anyarch
        elif pedantic and 'arch' in dictionary:
            war('package %s specifies an arch which is not enabled in config' % self.name)

        if Setup.using_buildtype:
            if 'buildtype' in dictionary:
                try:
                    self.buildtype = dictionary['buildtype']
                except:
                    raise Exceptio('invalid buildtype "%s" %s' %
                                   (dictionary['buildtype'], path), ErrorCode.COMPACT_PARSE_ERROR)
            else:
                self.buildtype = buildtype_unknown
        elif pedantic and 'buildtype' in dictionary:
            war('package %s specifies an buildtype which is not enabled in config' % self.name)

        deb('%s' % self.to_extra_string())

        try:
            dependencies = dictionary['depends']

            if dependencies:
                if not self.dependencies:
                    self.dependencies = []
                _ = Indent()

                for dependency in dependencies:
                    package = Package(None, None, dependency)
                    package_copy = copy.deepcopy(package)
                    package.parent = self
                    # inherit optionals from the package if they are unspecified. The downside is that they will no
                    # longer look exactly as they appear in the package file, the upside is that they now tell
                    # explicitly what their minimum requirement is.
                    if Setup.using_track:
                        if package.track == Track.anytrack:
                            package.track = self.track
                    if Setup.using_arch:
                        if package.arch == anyarch:
                            package.arch = self.arch
                        if self.arch != anyarch and package.arch != self.arch:
                            package.add_error(
                                Error(ErrorCode.ARCH_MISMATCH, package, 'parent is %s' % self.to_string()))
                    if Setup.using_buildtype:
                        if package.buildtype == buildtype_unknown:
                            package.buildtype = self.buildtype

                    if package_copy != package:
                        deb('%s -> %s (inherited values)' % (package_copy.to_extra_string(), package.to_extra_string()))

                    self.dependencies.append(package)
                del(_)

        except KeyError:
            pass
        except Exception as e:
            log.critical('Package caught %s' % str(e))
            raise e

    def from_package_path(self, package_path):
        if package_path.endswith('obsoleta.json'):
            self.package_path = os.path.dirname(package_path)

        json_file = get_package_filepath(self.package_path)

        with open(json_file) as f:
            _json = f.read()
            dictionary = json.loads(_json)
            self.unmodified_dict = dictionary
            if 'slot' in dictionary:
                self.layout = Layout.slot
                key_file = get_key_filepath(self.package_path)

                self.key = self.get_key_from_keyfile(key_file)
                base = dictionary['slot']
                try:
                    slot = dictionary[self.key]
                except KeyError:
                    raise Exceptio('failed to find slot in package file %s with key "%s"' %
                                   (os.path.abspath(json_file), self.key), ErrorCode.INVALID_KEY_FILE)

                final = dict(base, **slot)
                deb('parsing %s:' % package_path)
                _ = Indent()
                self.from_dict(final)
                del (_)
            elif 'multislot' in dictionary:
                raise Exceptio('internal error #0170', ErrorCode.UNKNOWN_EXCEPTION)
            else:
                deb('parsing %s:' % package_path)
                _ = Indent()
                self.from_dict(dictionary)
                del (_)

    def from_multislot_package_path(self, package_path, key_file):
        self.layout = Layout.multislot
        if package_path.endswith('obsoleta.json'):
            self.package_path = os.path.dirname(package_path)

        json_file = get_package_filepath(self.package_path)

        with open(json_file) as f:
            _json = f.read()
            dictionary = json.loads(_json)
            self.unmodified_dict = dictionary
            self.key = self.get_key_from_keyfile(key_file)
            base = dictionary['multislot']
            try:
                slot = dictionary[self.key]
            except KeyError:
                raise Exceptio('failed to find multislot in package file %s with key "%s"' %
                               (os.path.abspath(json_file), self.key), ErrorCode.INVALID_KEY_FILE)
            final = dict(base, **slot)
            self.from_dict(final)

    def get_key_from_keyfile(self, keyfile):
        try:
            with open(keyfile) as f:
                _json = f.read()
                dictionary = json.loads(_json)
                return dictionary['key']
        except FileNotFoundError as e:
            raise Exceptio(str(e) + ' ' + keyfile, ErrorCode.MISSING_KEY_FILE)
        except json.JSONDecodeError as e:
            raise Exceptio(str(e) + ' ' + keyfile, ErrorCode.INVALID_KEY_FILE)
        except Exception as e:
            raise Exceptio(str(e) + ' ' + keyfile, ErrorCode.UNKNOWN_EXCEPTION)

    @staticmethod
    def is_multislot(package_file):
        with open(package_file) as f:
            _json = f.read()
            dictionary = json.loads(_json)
            return 'multislot' in dictionary

    def get_slot_packages(self):
        return self.slot_packages

    def from_compact(self, compact):
        self.name = '*'
        self.version = Version('*')
        optionals = 0
        if Setup.using_track:
            self.track = Track.anytrack
            optionals += 1
        if Setup.using_arch:
            self.arch = anyarch
            optionals += 1
        if Setup.using_buildtype:
            self.buildtype = buildtype_unknown
            optionals += 1

        compact = compact.replace("'*'", '*')

        if compact != '*' and compact != 'all':
            entries = compact.split(':')
            found_entries = len(entries)
            expected_entries = 2 + optionals
            if found_entries > expected_entries:
                raise Exceptio('compact name contains %i fields but expected %i fields (check optionals)' %
                               (found_entries, expected_entries), ErrorCode.COMPACT_PARSE_ERROR)
            try:
                current = 'name'
                self.name = entries.pop(0)

                current = 'version'
                ver = entries.pop(0)
                if not ver:
                    ver = '*'
                self.version = Version(ver)

                if Setup.using_track:
                    current = 'track'
                    track = entries.pop(0)
                    if track:
                        self.track = Track[track]
                    else:
                        self.track = Track.anytrack
                if Setup.using_arch:
                    current = 'arch'
                    arch = entries.pop(0)
                    if arch:
                        self.arch = arch
                    else:
                        self.arch = anyarch
                if Setup.using_buildtype:
                    current = 'buildtype'
                    buildtype = entries.pop(0)
                    if buildtype:
                        self.buildtype = buildtype
                    else:
                        self.buildtype = buildtype_unknown
            except IndexError:
                pass
            except KeyError as e:
                raise Exceptio('failed to parse %s as %s' % (str(e), current), ErrorCode.COMPACT_PARSE_ERROR)
            except Exception as e:
                raise Exceptio(str(e), ErrorCode.COMPACT_PARSE_ERROR)

    def to_dict(self):
        dictionary = {
            'name': self.name,
            'version': str(self.version)
        }

        if Setup.using_track and self.track != Track.anytrack:
            dictionary['track'] = TrackToString[self.track.value]

        if Setup.using_arch and self.arch != anyarch:
            dictionary['arch'] = self.arch

        if Setup.using_buildtype and self.buildtype != buildtype_unknown:
            dictionary['buildtype'] = self.buildtype

        if self.dependencies:
            deps = []
            for dependency in self.dependencies:
                deps.append(dependency.to_dict())
            dictionary['depends'] = deps

        return dictionary

    def to_unmodified_dict(self):
        return self.unmodified_dict

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def set_version(self, version):
        self.version = version

    def get_track_as_string(self):
        return TrackToString[self.track.value]

    def get_path(self):
        return self.package_path

    def get_key(self):
        return self.key

    def to_string(self):
        # The fully unique identifier string for a package
        optionals = ''
        if Setup.using_track:
            optionals = ':%s' % TrackToString[self.track.value]
        if Setup.using_arch:
            optionals = '%s:%s' % (optionals, self.arch)
        if Setup.using_buildtype:
            optionals = '%s:%s' % (optionals, self.buildtype)
        return '%s:%s%s' % (self.name, str(self.version), optionals)

    def to_extra_string(self):
        # As to_string() but adds the errorcount in case there are errors, and dependencies if there are any.
        # Only used for printing
        extra = ''
        if not self.direct_dependency:
            extra += ':(lookup)'
        if self.errors:
            extra += ':(errors=%i)' % len(self.errors)
        if self.dependencies:
            extra += ':[depends='
            for dependency in self.dependencies:
                extra += '%s;' % dependency.to_string()
            extra += ']'
        return self.to_string() + extra

    def __str__(self):
        return self.to_extra_string()

    def __repr__(self):
        return self.to_string()

    def __eq__(self, other):
        if self.name != '*' and other.name != '*':
            if self.name != other.name or self.version != other.version:
                return False

        optionals = True
        if Setup.using_track:
            if other.track != Track.anytrack:
                optionals = optionals and self.track == other.track
        if Setup.using_arch:
            if other.arch != anyarch:
                optionals = optionals and self.arch == other.arch
        if Setup.using_buildtype:
            if other.buildtype != buildtype_unknown:
                optionals = optionals and self.buildtype == other.buildtype
        return optionals

    def equal_or_better(self, other):
        if self.name != '*' and other.name != '*':
            if self.name != other.name or self.version != other.version:
                return False

        optionals = True
        if Setup.using_track:
            if other.track == Track.production:
                optionals = self.track == Track.production
            else:
                optionals = optionals and self.track >= other.track
        if Setup.using_arch:
            optionals = optionals and (self.arch == anyarch or self.arch == other.arch)
        if Setup.using_track and Setup.using_buildtype:
            optionals = optionals and (self.track != Track.production or self.buildtype == other.buildtype)
        return optionals

    def matches_without_version(self, other):
        match = self.name == other.name
        if Setup.using_track:
            match = match and self.track == other.track
        if Setup.using_arch:
            match = match and self.arch == other.arch
        if Setup.using_buildtype:
            match = match and self.buildtype == other.buildtype
        return match

    def __lt__(self, other):
        return self.version < other.version

    def __hash__(self):
        return hash(self.to_string())

    def dump(self, ret, error):
        title = Indent.indent() + self.to_string()
        if self.errors:
            for err in self.errors:
                title += '\n' + Indent.indent() + ' - ' + err.to_string()
                error = err.get_error()
        ret.append(title)
        if self.dependencies:
            _ = Indent()
            for dependency in self.dependencies:
                error = dependency.dump(ret, error)
            del _
        return error

    def get_dependency(self, depends_package):
        try:
            depends_package = Package.construct_from_compact(depends_package)
        except:
            pass
        for dependency in self.dependencies:
            if dependency == depends_package:
                return dependency
        return None

    def get_dependencies(self):
        return self.dependencies

    def add_dependency(self, package):
        try:
            self.dependencies.append(package)
        except:
            self.dependencies = [package]

    def get_root_error(self):
        return self.errors

    def get_errors(self, errors=[]):
        if self.errors:
            errors += self.errors
        if self.dependencies:
            for dependency in self.dependencies:
                dependency.get_errors(errors)
        return errors

    def add_error(self, error):
        if not self.errors:
            self.errors = []
        self.errors.append(error)

    def set_lookup(self):
        self.direct_dependency = False
        if self.dependencies:
            for dependency in self.dependencies:
                dependency.direct_dependency = False

    def search_upstream(self, package_under_test=None, found=False):
        if not package_under_test:
            package_under_test = self
        else:
            deb('checking if upstream %s is the same as %s' % (str(self), package_under_test.to_string()))

        if self.parent:
            if self.parent.get_name() == package_under_test.get_name():
                log.info('circular dependency found for package ' + package_under_test.to_string())
                return True
            else:
                found = self.parent.search_upstream(package_under_test)
        return found