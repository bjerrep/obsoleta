from log import logger as log
from log import Indent as Indent
from log import deb, inf, war
from version import Version, VersionAny
from common import Error, get_package_filepath, get_key_filepath
from errorcodes import ErrorCode
from exceptions import BadPackageFile, MissingKeyFile, InvalidKeyFile
from exceptions import CompactParseError, UnknownException, IllegalDependency
from enum import Enum
import json, os, copy


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

    def __gt__(self, other):
        return self.value > other.value


TrackToString = ['defective', 'discontinued', 'anytrack', 'development', 'testing', 'production']


def track_from_string(string):
    return Track(TrackToString.index(string))


class Layout(Enum):
    standard = 0
    slot = 1
    multislot = 2


class Package:
    def __init__(self, setup, package_path, compact, dictionary, key_file=None):
        self.setup = setup
        self.parent = None
        self.package_path = package_path
        self.dependencies = None
        self.original_dependencies = None
        self.direct_dependency = True
        self.implicit_attributes = {}
        self.errors = None
        self.key = None
        self.original_dict = None
        self.layout = Layout.standard
        self.string = None
        self.slot_unresolved = False

        if compact:
            self.from_compact(compact, package_path)
        elif package_path:
            self.from_package_path(package_path, key_file, dictionary)
        else:
            self.from_dict(dictionary)

    @classmethod
    def construct_from_dict(cls, setup, dictionary):
        return cls(setup, None, None, dictionary)

    @classmethod
    def construct_from_package_path(cls, setup, package_path, key_file=None, dictionary=None):
        """ Returns the package object for package at the given path. A multislot package
            requires the specific keyfile to use (there might be more than one) """
        return cls(setup, package_path, None, dictionary, key_file)

    @classmethod
    def construct_from_compact(cls, setup, compact, package_path=None):
        return cls(setup, package_path, compact, None)

    @classmethod
    def auto_package(self, setup, package_or_compact):
        """
        Returns a Package object from its compact name. As a convenience it will
        just return the Package if it is given a Package.
        """
        if package_or_compact is None:
            return None
        if isinstance(package_or_compact, Package):
            return package_or_compact
        return Package.construct_from_compact(setup, package_or_compact)

    def from_dict(self, dictionary):
        if not self.original_dict:
            self.original_dict = dictionary

        if dictionary.get('path'):
            # a cache file will have the path added
            path = get_package_filepath(dictionary.get('path'))
        else:
            path = 'unknown'

        try:
            self.name = dictionary['name']
            self.version = Version(dictionary['version'])
        except:
            raise BadPackageFile('invalid name and/or version number in %s' % path)

        # track, arch and buildtype are deliberately left undefined if they are disabled
        pedantic = True
        if self.setup.using_track:
            if 'track' in dictionary:
                try:
                    self.track = Track[dictionary['track']]
                except KeyError:
                    raise CompactParseError('invalid track name "%s" %s' %
                                            (dictionary['track'], path))
            else:
                self.track = Track.anytrack
        elif pedantic and 'track' in dictionary:
            war('package %s specifies a track but track is not currently enabled (check config file)' % self.name)

        if self.setup.using_arch:
            try:
                self.arch = dictionary["arch"]
            except:
                self.arch = anyarch
        elif pedantic and 'arch' in dictionary:
            war('package %s specifies an arch but arch is not currently enabled (check config file)' % self.name)

        if self.setup.using_buildtype:
            if 'buildtype' in dictionary:
                try:
                    self.buildtype = dictionary['buildtype']
                except:
                    raise CompactParseError('invalid buildtype "%s" %s' %
                                           (dictionary['buildtype'], path))
            else:
                self.buildtype = buildtype_unknown
        elif pedantic and 'buildtype' in dictionary:
            war('package %s specifies an buildtype but buildtype is not currently enabled '
                '(check config file)' % self.name)

        try:
            dependencies = dictionary['depends']

            if dependencies:
                if not self.dependencies:
                    self.dependencies = []
                _ = Indent()

                for dependency in dependencies:
                    package = Package(self.setup, None, None, dependency)
                    package_copy = copy.copy(package)
                    package.parent = self
                    # inherit optionals from the package if they are unspecified. The downside is that they will no
                    # longer look exactly as they appear in the package file, the upside is that they now tell
                    # explicitly what their minimum requirement is.
                    if self.setup.using_track:
                        if package.track == Track.anytrack:
                            package.track = self.track
                    if self.setup.using_arch:
                        if package.arch == anyarch:
                            package.arch = self.arch
                        if self.arch != anyarch and package.arch != self.arch:
                            package.add_error(
                                Error(ErrorCode.ARCH_MISMATCH, package, 'parent is %s' % self.to_string()))
                    if self.setup.using_buildtype:
                        if package.buildtype == buildtype_unknown:
                            package.buildtype = self.buildtype

                    if package_copy != package:
                        deb('%s -> %s (inherited values)' % (package_copy.to_extra_string(), package.to_extra_string()))

                    self.dependencies.append(package)
                del(_)
                self.dependencies.sort()
                self.original_dependencies = self.dependencies

        except KeyError:
            pass
        except Exception as e:
            log.critical('Package caught %s' % str(e))
            raise e

    def verify_merge_tracks(self, dict):
        """ Sanity check that the tracks are valid after a multislot merge. A downstream track can't
            be at a higher track than any upstreams.
        """
        dependencies = dict.get("depends")
        if dependencies is None:
            return
        track = dict.get("track")
        if not track:
            track = Track.anytrack.name
        for dependency in dependencies:
            dep_track = dependency.get("track")
            if dep_track and (track_from_string(track) > track_from_string(dep_track)):
                message = ("Downstream package %s with track '%s' can't depend on %s with track '%s'. (%s)" %
                          (dict['name'], track, dependency['name'], dep_track, str(dict.get('arch'))))
                raise IllegalDependency(message)

    def merge(self, slot_section, key_section):
        """
        Add new or replace existing entries in the slot_section with entries from the key_section.
        The yikes-ness arises when individuel entries in the 'depends' lists are merged as well.
        """
        result = dict(slot_section, **key_section)

        if key_section.get('depends'):
            if not slot_section.get('depends'):
                slot_section['depends'] = []

            new_entries = copy.copy(key_section['depends'])
            for key_depends in key_section['depends']:
                for slot_depends in slot_section['depends']:
                    if key_depends['name'] == slot_depends['name']:
                        new_entries.append(dict(slot_depends, **key_depends))
                        break
                    if slot_depends not in new_entries:
                        new_entries.append(slot_depends)

            result['depends'] = new_entries
        self.verify_merge_tracks(result)
        return result

    def from_package_path(self, package_path, multislot_key_file, dictionary=None):
        if package_path.endswith('obsoleta.json'):
            self.package_path = os.path.dirname(package_path)

        if not dictionary:
            json_file = get_package_filepath(self.package_path)

            # a lazy toolchain might be camping in a multislot build directory which is wrong but just for the
            # fun of it, lets allow that. (it should have been in the up dir and supplied a --keypath)
            # So if we have a key file, and there is a package file in the up dir, lets silently relocate
            # and go with that further below. If all this sounds awful then set 'relaxed_multislot' to false.
            try:
                if self.setup.relaxed_multislot and not multislot_key_file and not os.path.exists(json_file):
                    key_file = os.path.join(self.package_path, 'obsoleta.key')
                    if os.path.exists(key_file):
                        updir = os.path.split(os.path.abspath(self.package_path))[0]
                        updir_package_file = get_package_filepath(updir)
                        if os.path.exists(updir_package_file):
                            inf('assuming that this is a multislotted build dir. Using package file %s' %
                                updir_package_file)
                            json_file = updir_package_file
                            multislot_key_file = key_file
            except:
                # there was an attempt, and it failed. Now just fall over
                pass

            with open(json_file) as f:
                _json = f.read()
                try:
                    dictionary = json.loads(_json)
                except:
                    raise BadPackageFile('malformed json in %s' % json_file)

        self.original_dict = dictionary

        _ = Indent()
        if 'slot' in dictionary:
            deb('parsing \'%s\' in %s (slot)' %
                (dictionary['slot']['name'], package_path))
            self.layout = Layout.slot

            key_file = get_key_filepath(self.package_path)
            self.key = self.get_key_from_keyfile(key_file)
            slot_section = dictionary['slot']

            try:
                key_section = dictionary[self.key]
            except KeyError:
                raise InvalidKeyFile('failed to find slot in package file %s with key "%s"' %
                                    (os.path.abspath(package_path), self.key))

            merged = self.merge(slot_section, key_section)
            self.from_dict(merged)
            inf('parsing \'%s\' in %s (slot) -> %s' %
                (dictionary['slot']['name'], package_path, self.to_string()))

        elif 'multislot' in dictionary:
            deb('parsing \'%s\' in %s (multislot)' %
                (dictionary['multislot']['name'], package_path))
            self.layout = Layout.multislot

            if not multislot_key_file:
                self.slot_unresolved = True
                self.from_dict(dictionary['multislot'])
                return

            try:
                multislot_key_file = get_key_filepath(multislot_key_file)
            except:
                raise InvalidKeyFile('missing or invalid keyfile "%s"' % multislot_key_file)

            try:
                self.key = self.get_key_from_keyfile(multislot_key_file)
            except Exception:
                self.key = self.get_key_from_keyfile(os.path.join(package_path, multislot_key_file))

            slot_section = dictionary['multislot']
            try:
                key_section = dictionary[self.key]
            except KeyError:
                raise InvalidKeyFile('failed to find multislot in package file %s with key "%s"' %
                                    (os.path.abspath(package_path), self.key))
            merged = self.merge(slot_section, key_section)
            self.from_dict(merged)
            inf('parsing \'%s\' in %s (multislot) -> %s' %
                (dictionary['multislot']['name'], package_path, self.to_string()))
        else:
            try:
                name = dictionary['name']
            except KeyError:
                raise BadPackageFile('missing name')
            self.from_dict(dictionary)
            inf('parsing \'%s\' in %s -> %s' % (name, package_path, self.to_string()))

    def get_key_from_keyfile(self, keyfile):
        try:
            with open(keyfile) as f:
                _json = f.read()
                dictionary = json.loads(_json)
                return dictionary['key']
        except FileNotFoundError:
            raise MissingKeyFile('%s not found' % keyfile)
        except json.JSONDecodeError as e:
            raise InvalidKeyFile(str(e) + ' ' + keyfile)
        except Exception as e:
            raise UnknownException(str(e) + ' ' + keyfile)

    def from_compact(self, compact, package_path):
        self.name = '*'
        self.version = VersionAny
        self.package_path = package_path
        optionals = 0
        if self.setup.using_track:
            self.track = Track.anytrack
            optionals += 1
        if self.setup.using_arch:
            self.arch = anyarch
            optionals += 1
        if self.setup.using_buildtype:
            self.buildtype = buildtype_unknown
            optionals += 1

        compact = compact.replace("'*'", '*')

        if compact != '*' and compact != 'all':
            entries = compact.split(':')
            found_entries = len(entries)
            expected_entries = 2 + optionals
            if found_entries > expected_entries:
                raise CompactParseError('compact name contains %i fields but expected %i fields (check optionals)' %
                                       (found_entries, expected_entries))
            try:
                current = 'name'
                self.name = entries.pop(0)

                current = 'version'
                ver = entries.pop(0)
                if not ver:
                    ver = '*'
                self.version = Version(ver)

                if self.setup.using_track:
                    current = 'track'
                    track = entries.pop(0)
                    if track:
                        self.track = Track[track]
                    else:
                        self.track = Track.anytrack
                if self.setup.using_arch:
                    current = 'arch'
                    arch = entries.pop(0)
                    if arch:
                        self.arch = arch
                    else:
                        self.arch = anyarch
                if self.setup.using_buildtype:
                    current = 'buildtype'
                    buildtype = entries.pop(0)
                    if buildtype:
                        self.buildtype = buildtype
                    else:
                        self.buildtype = buildtype_unknown
            except IndexError:
                pass
            except KeyError as e:
                raise CompactParseError('failed to parse %s as %s' % (str(e), current))
            except Exception as e:
                raise CompactParseError(str(e))

    def to_dict(self, add_path=False):
        dictionary = {
            'name': self.name,
            'version': str(self.version)
        }

        if self.setup.using_track and self.track != Track.anytrack:
            dictionary['track'] = TrackToString[self.track.value]

        if self.setup.using_arch and self.arch != anyarch:
            dictionary['arch'] = self.arch

        if self.setup.using_buildtype and self.buildtype != buildtype_unknown:
            dictionary['buildtype'] = self.buildtype

        if add_path and self.package_path:
            dictionary['path'] = self.package_path

        if self.dependencies:
            deps = []
            for dependency in self.dependencies:
                deps.append(dependency.to_dict(add_path))
            dictionary['depends'] = deps

        return dictionary

    def get_original_dict(self):
        return self.original_dict

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_arch(self, implicit=False):
        if not implicit or self.arch != anyarch:
            return self.arch
        try:
            return self.implicit_attributes['arch']
        except:
            return self.arch

    def get_track(self, implicit=False):
        if not implicit or self.track != Track.anytrack:
            return self.track
        try:
            return self.implicit_attributes['track']
        except:
            return self.track

    def get_buildtype(self, implicit=False):
        if not implicit or self.buildtype != buildtype_unknown:
            return self.buildtype
        try:
            return self.implicit_attributes['buildtype']
        except:
            return self.buildtype

    def set_implicit(self, key, value):
        self.implicit_attributes[key] = value

    def set_version(self, version):
        self.string = None
        self.version = version

    def get_path(self):
        return self.package_path

    def get_parent(self):
        return self.parent

    def get_depends_path(self, depends_package):
        return self.get_dependency(depends_package).package_path

    def get_key(self):
        return self.key

    def get_value(self, key):
        return self.original_dict[key]

    def set_value(self, key, value, depend_name=None):
        if depend_name:
            for dependency in self.get_dependencies():
                if dependency.get_name() == depend_name:
                    self.original_dict['depends'][0][key] = value
        else:
            self.original_dict[key] = value

    def to_string(self):
        # The fully unique identifier string for a package
        if self.string:
            return self.string
        if self.setup.using_all_optionals:
            self.string = '%s:%s:%s:%s:%s' % (self.name, str(self.version),
                                              TrackToString[self.track.value],
                                              self.arch, self.buildtype)
        else:
            optionals = ''
            if self.setup.using_track:
                optionals = ':%s' % TrackToString[self.track.value]
            if self.setup.using_arch:
                optionals = '%s:%s' % (optionals, self.arch)
            if self.setup.using_buildtype:
                optionals = '%s:%s' % (optionals, self.buildtype)
            self.string = '%s:%s%s' % (self.name, str(self.version), optionals)
        return self.string

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
        """ The equality check uses the set of rules that exists for checking for equality for
            each of the name, version, track, arch and buildtypes attributes. For some specific examples
            of how versions are checked see 'test_versions.py' and for the rest they honor the
            wildcards anytrack, anyarch and unknown for buildtype. The current rule that the
            'production' track may not be mixed with other tracks are also enforced here.
        """
        if other.name != '*' and (self.name != other.name or self.version != other.version):
            return False

        if self.setup.using_track:
            if other.track == Track.production and self.track != Track.production:
                return False
            if not (self.track >= other.track):
                return False
        if self.setup.using_arch:
            if not (self.arch == anyarch or other.arch == anyarch or self.arch == other.arch):
                return False

        # if any tracks are production then different explicit tracks are not allowed and on top
        # of that the buildtypes must match. Might be a bogus rule that needs to go.
        if self.setup.using_track and self.setup.using_buildtype:
            if self.track == Track.production or other.track == Track.production:
                if self.track == other.track or self.track == Track.anytrack or other.track == Track.anytrack:
                    # yes, both are production or can mix. Disallow different explicit build types
                    return (self.buildtype == other.buildtype or
                            self.buildtype == buildtype_unknown or
                            other.buildtype == buildtype_unknown)
        return True

    def is_duplicate(self, other):
        match = self.name == other.name
        if self.setup.using_arch and match:
            match = self.arch == other.arch
        return match

    def __lt__(self, other):
        return self.version < other.version

    def __hash__(self):
        return hash(self.to_string())

    def dump(self, ret, error=None, skip_dependencies=False):
        if error.has_error():
            return error

        if self.errors:
            return self.errors[0]

        title = Indent.indent() + self.to_string()
        ret.append(title)

        if not skip_dependencies and self.dependencies:
            _ = Indent()
            for dependency in self.dependencies:
                error = dependency.dump(ret, error)
            del _
        return error

    def get_dependency(self, depends_package):
        """ Always prepare for getting a None in return, especially when it definitely
            wasn't expected
        """
        for dependency in self.dependencies:
            if dependency == depends_package:
                return dependency
        return None

    def get_dependencies(self):
        """ Return the dependencies. Once the dependencies are resolved (by obsoleta) these
            dependencies are replaced with the resolved upstreams.
        """
        return self.dependencies

    def get_original_dependencies(self):
        """ Return the dependencies as they were loaded from package file.
        """
        return self.original_dependencies

    def get_nof_dependencies(self):
        try:
            return len(self.dependencies)
        except:
            return 0

    def add_dependency(self, package):
        try:
            self.dependencies.append(package)
        except:
            self.dependencies = [package]

    def get_root_error(self):
        return self.errors

    def error_list_append(self, error_list):
        if self.errors:
            error_list.extend(self.errors)
        if self.dependencies:
            for dependency in self.dependencies:
                dependency.error_list_append(error_list)
        return error_list

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

    def get_layout(self):
        return Layout(self.layout).name
