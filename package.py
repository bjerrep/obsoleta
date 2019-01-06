from log import logger as log
from version import Version
from common import Setup, ErrorCode, Error, IllegalPackage, Indent
import json
import os
from enum import Enum


buildtype_unknown = 'unknown'
anyarch = 'anyarch'


class Track(Enum):
    defective = 0
    discontinued = 1
    ANY = 2
    development = 3
    testing = 4
    production = 5

    def __ge__(self, other):
        return self.value >= other.value


TrackToString = ['defective', 'discontinued', 'anytrack', 'development', 'testing', 'production']


class Package:
    def __init__(self, packagepath, compact, dictionary):
        self.parent = None
        self.packagepath = packagepath
        self.dependencies = None
        self.direct_dependency = True
        self.errors = None

        if packagepath:
            if not packagepath.endswith('obsoleta.json'):
                self.packagepath = os.path.join(packagepath, 'obsoleta.json')
            with open(self.packagepath) as f:
                log.debug('[parsing file %s]' % self.packagepath)
                _json = f.read()
                dictionary = json.loads(_json)
                self.from_dict(dictionary)
        elif compact:
            self.from_compact(compact)
        else:
            self.from_dict(dictionary)

    @classmethod
    def construct_from_dict(cls, dictionary):
        return cls(None, None, dictionary)

    @classmethod
    def construct_from_packagepath(cls, packagepath):
        return cls(packagepath, None, None)

    @classmethod
    def construct_from_compact(cls, compact):
        return cls(None, compact, None)

    def from_dict(self, dictionary):
        self.name = dictionary['name']
        try:
            self.version = Version(dictionary['version'])
        except:
            raise IllegalPackage('invalid version number in %s' % self.packagepath)

        # track, arch and buildtype are deliberately left undefined if they are disabled
        if Setup.using_track:
            if 'track' in dictionary:
                try:
                    self.track = Track[dictionary['track']]
                except KeyError:
                    raise IllegalPackage('invalid track name "%s" in %s' % (dictionary['track'], self.packagepath))
            else:
                self.track = Track.ANY

        if Setup.using_arch:
            try:
                self.arch = dictionary["arch"]
            except:
                self.arch = anyarch

        if Setup.using_buildtype:
            if 'buildtype' in dictionary:
                try:
                    self.buildtype = dictionary['buildtype']
                except:
                    raise IllegalPackage('invalid buildtype "%s" in %s' % (dictionary['buildtype'], self.packagepath))
            else:
                self.buildtype = buildtype_unknown

        log.debug(Setup.indent + '%s' % self.to_extra_string())

        try:
            dependencies = dictionary['depends']

            if dependencies:
                if not self.dependencies:
                    self.dependencies = []
                _i = Indent()

            for dependency in dependencies:
                package = Package(None, None, dependency)
                package.parent = self
                # inherit optionals from the package if they are unspecified. The downside is that they will no
                # longer look exactly as they appear in the package file, the upside is that they now tell
                # explicitly what their minimum requirement is.
                if Setup.using_track:
                    if package.track == Track.ANY:
                        package.track = self.track
                if Setup.using_arch:
                    if package.arch == anyarch:
                        package.arch = self.arch
                    if self.arch != anyarch and package.arch != self.arch:
                        package.add_error(Error(ErrorCode.ARCH_MISMATCH, package, 'parent is %s' % self.to_string()))
                if Setup.using_buildtype:
                    if package.buildtype == buildtype_unknown:
                        package.buildtype = self.buildtype

                self.dependencies.append(package)

        except KeyError:
            pass
        except Exception as e:
            log.critical('Package caught %s' % str(e))
            raise e

    def from_packagepath(self, packagepath):
        if not packagepath.endswith('obsoleta.json'):
            self.packagepath = os.path.join(packagepath, 'obsoleta.json')
        with open(self.packagepath) as f:
            log.debug('[parsing file %s]' % self.packagepath)
            dictionary = json.loads(f.read())
            self.construct_from_dict(dictionary)

    def from_compact(self, compact):
        self.name = '*'
        self.version = Version('*')
        if Setup.using_track:
            self.track = Track.ANY
        if Setup.using_arch:
            self.arch = anyarch
        if Setup.using_buildtype:
            self.buildtype = buildtype_unknown

        if compact != '*' and compact != 'all':
            entries = compact.split(':')
            try:
                self.name = entries.pop(0)
                if Setup.using_track:
                    self.track = Track[entries.pop(0)]
                if Setup.using_arch:
                    self.arch = entries.pop(0)
                if Setup.using_buildtype:
                    self.buildtype = entries.pop(0)
                self.version = Version(entries.pop(0))
            except:
                pass

    def to_dict(self):
        dictionary = {
            'name': self.name,
            'version': str(self.version)
        }

        if Setup.using_track and self.track != Track.ANY:
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

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_path(self):
        return self.packagepath

    def to_string(self):
        # The fully unique identifier string for a package
        optionals = ''
        if Setup.using_track:
            optionals = '%s:' % TrackToString[self.track.value]
        if Setup.using_arch:
            optionals = '%s%s:' % (optionals, self.arch)
        if Setup.using_buildtype:
            optionals = '%s%s:' % (optionals, self.buildtype)
        return '%s:%s%s' % (self.name, optionals, str(self.version))

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
            if other.track != Track.ANY:
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
        match = self.name == other.name and \
                self.track == other.track and \
                self.arch == other.arch and \
                self.buildtype == other.buildtype
        return match

    def __lt__(self, other):
        return self.version < other.version

    def __hash__(self):
        return hash(self.to_string())

    def dump(self, ret, error):
        title = Setup.indent + self.to_string()
        if self.errors:
            for err in self.errors:
                title += "\n" + Setup.indent + ' - ' + err.to_string()
                error = err.get_error()
        ret.append(title)
        if self.dependencies:
            _i2 = Indent()
            for dependency in self.dependencies:
                error = dependency.dump(ret, error)
            del _i2
        return error

    def get_dependencies(self):
        return self.dependencies

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
            log.debug(Setup.indent + 'checking if upstream %s is the same as %s' % (str(self), package_under_test.to_string()))

        if self.parent:
            if self.parent.get_name() == package_under_test.get_name():
                log.info(Setup.indent + 'circular dependency found for package ' + package_under_test.to_string())
                return True
            else:
                found = self.parent.search_upstream(package_under_test)
        return found
