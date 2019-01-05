#!/usr/bin/env python3
from enum import Enum
import json
import argparse
from log import logger as log
import logging
import os
import copy
from common import ErrorCode, Error, NoPackage, IllegalPackage
from version import Version
import collections

indent = ''

class Indent():
    def __init__(self):
        global indent;
        indent += '  '

    def __del__(self):
        global indent
        indent = indent[:-3]


using_track = False
using_arch = False
using_buildtype = False
buildtype_unknown = "unknown"

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
    def __init__(self, packagepath, compact=None, dictionary=None):
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
                dictionary = json.loads(f.read())
                self.construct_from_dict(dictionary)
        elif compact:
            self.construct_from_compact(compact)
        else:
            self.construct_from_dict(dictionary)

    def construct_from_dict(self, dictionary):

        self.name = dictionary["name"]

        try:
            self.version = Version(dictionary["version"])
        except:
            raise IllegalPackage("invalid version number in %s" % self.packagepath)

        # track, arch and buildtype are deliberately left undefined if they are disabled
        if using_track:
            if 'track' in dictionary:
                try:
                    self.track = Track[dictionary['track']]
                except KeyError:
                    raise IllegalPackage('invalid track name "%s" in %s' % (dictionary['track'], self.packagepath))
            else:
                self.track = Track.ANY

        if using_arch:
            try:
                self.arch = dictionary["arch"]
            except:
                self.arch = "anyarch"

        if using_buildtype:
            if 'buildtype' in dictionary:
                try:
                    self.buildtype = dictionary["buildtype"]
                except:
                    raise IllegalPackage('invalid buildtype "%s" in %s' % (dictionary['buildtype'], self.packagepath))
            else:
                self.buildtype = buildtype_unknown

        log.debug(indent + '%s' % self.to_extra_string())

        try:
            dependencies = dictionary["depends"]

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
                if using_track:
                    if package.track == Track.ANY:
                       package.track = self.track
                if using_arch:
                    if package.arch == 'anyarch':
                        package.arch = self.arch
                    if self.arch != 'anyarch' and package.arch != self.arch:
                        package.add_error(Error(ErrorCode.ARCH_MISMATCH, package, 'parent is %s' % self.to_string()))
                if using_buildtype:
                    if package.buildtype == buildtype_unknown:
                        package.buildtype = self.buildtype

                self.dependencies.append(package)

        except KeyError:
            pass
        except Exception as e:
            log.critical("Package caught %s" % str(e))
            raise e

    def construct_from_compact(self, compact):
        self.name = '*'
        self.version = Version('*')
        if using_track:
            self.track = Track.ANY
        if using_arch:
            self.arch = 'anyarch'
        if using_buildtype:
            self.buildtype = buildtype_unknown

        if compact != '*' and compact != 'all':
            entries = compact.split(':')
            try:
                self.name = entries.pop(0)
                if using_track:
                    self.track = Track[entries.pop(0)]
                if using_arch:
                    self.arch = entries.pop(0)
                if using_buildtype:
                    self.buildtype = entries.pop(0)
                self.version = Version(entries.pop(0))
            except:
                pass

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_path(self):
        return self.packagepath

    def to_string(self):
        # The fully unique identifier string for a package
        optionals = ''
        if using_track:
            optionals = "%s:" % TrackToString[self.track.value]
        if using_arch:
            optionals = "%s%s:" % (optionals, self.arch)
        if using_buildtype:
            optionals = "%s%s:" % (optionals, self.buildtype)
        return "%s:%s%s" % (self.name, optionals, str(self.version))

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
        if using_track:
            if other.track != Track.ANY:
                optionals = optionals and self.track == other.track
        if using_arch:
            if other.arch != 'anyarch':
                optionals = optionals and self.arch == other.arch
        if using_buildtype:
            if other.buildtype != 'unknown':
                optionals = optionals and self.buildtype == other.buildtype
        return optionals

    def equal_or_better(self, other):
        if self.name != '*' and other.name != '*':
            if self.name != other.name or self.version != other.version:
                return False

        optionals = True
        if using_track:
            if other.track == Track.production:
                optionals = self.track == Track.production
            else:
                optionals = optionals and (self.track == Track.ANY or self.track >= other.track)
        if using_arch:
            optionals = optionals and (self.arch == "anyarch" or self.arch == other.arch)
        if using_track and using_buildtype:
            optionals = optionals and (self.track != Track.production or self.buildtype == other.buildtype)
        return optionals

    def matches_without_version(self, other):
        match = self.name == other.name and self.track == other.track and self.arch == other.arch and self.buildtype == other.buildtype
        return match

    def __lt__(self, other):
        return self.version < other.version

    def __hash__(self):
        return hash(self.to_string())

    def dump(self, ret, error, indent='', root=True):
        title = indent + self.to_string()
        if self.errors:
            for err in self.errors:
                title += "\n" + indent + '     - ' + err.to_string()
                error = err.get_error()
        ret.append(title)
        if self.dependencies:
            for dependency in self.dependencies:
                error = dependency.dump(ret, error, indent + '  ', root=False)
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
            log.debug(indent + 'checking if upstream %s is the same as %s' % (str(self), package_under_test.to_string()))

        if self.parent:
            if self.parent.get_name() == package_under_test.get_name():
                log.info(indent + 'circular dependency found for package ' + package_under_test.to_string())
                return True
            else:
                found = self.parent.search_upstream(package_under_test)
        return found


class Obsoleta:
    def __init__(self, paths):
        self.dirs_checked = 0
        self.base_paths = paths
        self.package_files = self.find_package_files(paths)

        self.loaded_packages = []
        self.load(self.package_files)

        if not self.loaded_packages:
            raise NoPackage("didn't find any packages")

        for package in self.loaded_packages:
            self.resolve_dependencies(package)

        self.check_for_multiple_versions()
        log.info('package loading and parsing complete')

    def find_packages_in_path(self, path, results=[], maxdepth=2):
        self.dirs_checked += 1
        for entry in os.scandir(path):
            if entry.is_dir():
                if maxdepth:
                    maxdepth -= 1
                    self.find_packages_in_path(entry.path, results, maxdepth)
                    maxdepth += 1
            if entry.name == 'obsoleta.json':
                results.append(entry.path)
                continue

        return results

    def find_package_files(self, pathlist):
        package_files = []
        for path in pathlist:
            package_files += self.find_packages_in_path(path)

        log.info('found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        return package_files

    def load(self, json_files):
        json_files = sorted(json_files)
        for file in json_files:
            package = Package(file)
            self.loaded_packages.append(package)

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            log.debug(indent + 'resolving root ' + str(package))
        else:
            log.debug(indent + 'resolving dependency ' + str(package))

        _1 = Indent()

        dependencies = package.get_dependencies()

        if dependencies:
            package.dependencies = []

            level += 1

            for dependency in dependencies:
                resolved = self.lookup(dependency)
                log.debug(indent + 'lookup gave "%s" for dependency %s' % (str(resolved), str(dependency)))

                _2 = Indent()

                if resolved:
                    resolved.parent = package
                    resolved = copy.deepcopy(resolved)
                    if level > 1:
                        resolved.set_lookup()
                    resolved_dependencies = resolved.get_dependencies()
                    if resolved_dependencies:
                        for d in resolved_dependencies:
                            circular_dependency = d.search_upstream()
                            if circular_dependency:
                                resolved.add_error(Error(ErrorCode.CIRCULAR_DEPENDENCY, d, 'required by ' + package.to_string()))
                                package.dependencies.append(resolved)
                                return False

                    package.dependencies.append(resolved)
                    self.resolve_dependencies(resolved, level)
                else:
                    resolved = copy.deepcopy(dependency)
                    if level > 1:
                        resolved.set_lookup()
                    resolved.add_error(Error(ErrorCode.PACKAGE_NOT_FOUND, resolved, 'required by ' + package.to_string()))
                    resolved.parent = package
                    package.dependencies.append(resolved)
                    log.debug(indent + 'package ' + dependency.to_string() + ' does not exist')

            level -= 1
        return True

    def lookup(self, target_package):
        candidates = []
        for package in self.loaded_packages:
            if package.equal_or_better(target_package):
                candidates.append(package)
        if not candidates:
            return None
        return max(candidates)

    def check_for_multiple_versions(self):
        log.info('checking for multiple versions:')
        _1 = Indent()

        for package in self.loaded_packages:
            package_list = []
            self.get_package_list(package, package_list)
            unique_packages = set(package_list)

            names = [p.get_name() for p in unique_packages]
            names = [name for name, count in collections.Counter(names).items() if count > 1]

            for name in names:
                candidate = []
                for _package in unique_packages:
                    if _package.get_name() == name:
                        candidate.append(_package)

                for i in range(len(candidate)):
                    for j in candidate[i+1:]:
                        if candidate[i].matches_without_version(j):
                            err1 = Error(ErrorCode.MULTIPLE_VERSIONS, candidate[i], "with parent %s" % candidate[i].parent)
                            log.error(indent + "ERROR: " + err1.to_string())
                            candidate[i].add_error(err1)

                            err2 = Error(ErrorCode.MULTIPLE_VERSIONS, j, "with parent %s" % j.parent)
                            log.error(indent + "ERROR: " + err2.to_string())
                            j.add_error(err2)

    def get_package_list(self, package, packages):
        packages.append(package)
        if package.dependencies:
            for dependency in package.dependencies:
                self.get_package_list(dependency, packages)
        return packages

    def dump_tree(self, root_package):
        ret = []
        error = ErrorCode.OK
        for package in self.loaded_packages:
            if package == root_package:
                error = package.dump(ret, error)
        return ret, error

    def dump_build_order(self, root_package):
        packages_build_order = []
        package_list = []
        for package in self.loaded_packages:
            if package == root_package:
                self.get_package_list(package, package_list)
        packages = set(package_list)
        deleted = []
        package_copy = packages
        found_next = True

        while found_next:
            found_next = False
            for package in package_copy:
                if not package.get_dependencies():
                    packages_build_order.append(package)
                    package_copy.remove(package)
                    deleted.append(package)
                    found_next = True
                    break
                nof_dependencies = len(package.get_dependencies())
                for dp in package.get_dependencies():
                    if dp in deleted:
                        nof_dependencies -= 1
                if not nof_dependencies:
                    packages_build_order.append(package)
                    package_copy.remove(package)
                    deleted.append(package)
                    found_next = True
                    break

        return package_copy, packages_build_order

    def get_errors(self, package):
        errors = []

        if self.loaded_packages:
            for loaded_package in self.loaded_packages:
                if loaded_package == package:
                    errors += loaded_package.get_errors()
                    package_list = []
                    package_list = set(self.get_package_list(loaded_package, package_list))
                    for _package in package_list:
                        for loaded_package in self.loaded_packages:
                            if loaded_package.get_name() == _package.get_name():
                                errors += loaded_package.get_errors()
                                _package.errors = loaded_package.errors

                    return list(set(errors))

        return ErrorCode.PACKAGE_NOT_FOUND


# ---------------------------------------------------------------------------------------------

obsoleta_root = os.path.dirname(__file__)

def print_error(message):
    print(message)


def print_message(message):
    print(message)


parser = argparse.ArgumentParser('obsoleta')
parser.add_argument('--package', dest='compact',
                    help='the package to investigate in compact form or "all". See also --json')
parser.add_argument('--json', dest='packagepath',
                    help='the path for the package to investigate. See also --package')

parser.add_argument('--check', action='store_true',
                    help='check a specified package')
parser.add_argument('--tree', action='store_true',
                    help='show tree for a package')
parser.add_argument('--buildorder', action='store_true',
                    help='show dependencies in building order for a package')

parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--path', action='store', dest='path',
                    help=': separated base path. Use this and/or paths in obsoleta.conf (There are no default path)')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')
parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')


results = parser.parse_args()

if results.verbose:
    log.setLevel(logging.DEBUG)

# go-no-go checks

if not results.compact and not results.packagepath:
    print_error('no package specified, see --package and --json')
    exit(ErrorCode.MISSING_INPUT.value)

if not results.tree and not results.check and not results.buildorder:
    print_error('no action specified, see --check, --tree and --buildorder')
    exit(ErrorCode.MISSING_INPUT.value)

# parse configuration file

try:
    paths = results.path.split(os.pathsep)
except:
    paths = []

conffile = os.path.join(obsoleta_root, 'obsoleta.conf')
if results.conffile:
    conffile = results.conffile
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
        using_arch = conf.get('using_arch') == 'on'
        using_track = conf.get('using_track') == 'on'
        using_buildtype = conf.get('using_buildtype') == 'on'
except FileNotFoundError:
    log.info('no configuration file %s found - continuing regardless' % conffile)

paths = [os.path.abspath(p) for p in paths if p]
paths = set(paths)

if not paths:
    print_error('no paths given from commandline and/or conf file, giving up')
    exit(ErrorCode.MISSING_INPUT.value)

log.info('searching %i paths' % len(paths))
for path in paths:
    log.info('  path = %s' % path)

# construct obsoleta, load and parse everything in one go

try:
    obsoleta = Obsoleta(paths)

except json.decoder.JSONDecodeError as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)
except FileNotFoundError as e:
    log.critical('directory not found: %s' % str(e))
    exit(ErrorCode.BAD_PATH.value)
except KeyError as e:
    log.critical('missing entry in package file: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)
except NoPackage as e:
    print_error('no packages found, giving up. Searched the path(s):')
    for path in paths:
        print_error('  %s' % path)
    exit(ErrorCode.PACKAGE_NOT_FOUND.value)
except Exception as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

exit_code = ErrorCode.UNSET

package = Package(results.packagepath, results.compact)

# and now figure out what to do

if results.check:
    log.info('checking package "%s"' % package)
    errors = obsoleta.get_errors(package)

    if errors == ErrorCode.PACKAGE_NOT_FOUND:
        print_error('package "%s" not found' % package)
        exit_code = errors
    elif errors:
        print_error('checking package "%s": failed, %i errors found' % (package, len(errors)))
        for error in errors:
            print_error('   ' + error.to_string())
            exit_code = error.get_error()
    else:
        print_message('checking package "%s": success' % package)
        exit_code = ErrorCode.OK

elif results.tree:
    log.info('package tree for "%s"' % package)
    dump, error = obsoleta.dump_tree(package)
    if dump:
        print_message("\n".join(dump))
        exit_code = error
    else:
        print_message("package not found")
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif results.buildorder:
    exit_code = ErrorCode.OK
    log.info('packages listed in buildorder')
    unresolved, resolved = obsoleta.dump_build_order(package)

    log.info('build order')
    if not resolved:
        print_error(' - unable to find somewhere to start')
    for _package in resolved:
        if results.printpaths:
            print_message(_package.get_path())
        else:
            print_message(_package.to_string())
        errors = _package.get_root_error()
        if errors:
            for error in errors:
                exit_code = error.get_error()
                print_error(' - error: ' + error.to_string())

    if unresolved:
        print_error('unable to resolve build order for the following packages (circular dependencies ?)')
        exit_code = ErrorCode.CIRCULAR_DEPENDENCY
        for _package in unresolved:
            print_error(' - ' + _package.to_string())

else:
    log.error("no valid command found")


exit(exit_code.value)
