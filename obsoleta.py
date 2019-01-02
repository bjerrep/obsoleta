#!/usr/bin/env python3
from enum import Enum
import json
import argparse
from log import logger as log
import logging
import os
import copy
from common import ErrorCode, Error, IllegalPackage
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
    def __init__(self, dict, path=None):
        self.parent = None
        self.path = path
        self.dependencies = []
        self.direct_dependency = True
        self.errors = []

        self.name = dict["name"]

        try:
            self.version = Version(dict["version"])
        except:
            raise IllegalPackage("invalid version number in %s" % self.path)

        # track, arch and buildtype are deliberately left undefined if they are disabled
        if using_track:
            if 'track' in dict:
                try:
                    self.track = Track[dict['track']]
                except KeyError:
                    raise IllegalPackage('invalid track name "%s" in %s' % (dict['track'], self.path))
            else:
                self.track = Track.ANY

        if using_arch:
            try:
                self.arch = dict["arch"]
            except:
                self.arch = "anyarch"

        if using_buildtype:
            if 'buildtype' in dict:
                try:
                    self.buildtype = dict["buildtype"]
                except:
                    raise IllegalPackage('invalid buildtype "%s" in %s' % (dict['buildtype'], self.path))
            else:
                self.buildtype = buildtype_unknown

        try:
            dependencies = dict["depends"]
            for dependency in dependencies:
                package = Package(dependency, path)
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

        # This will list any dependencies as they get parsed, before the package itself, but this way the
        # dependencies for the package itself when it is printed will be in the inherited form.
        log.debug('  %s' % self.to_extra_string())

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_path(self):
        return self.path

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
        if self.name != other.name or self.version != other.version:
            return False

        optionals = True
        if using_track:
            optionals = optionals and self.track == other.track
        if using_arch:
            optionals = optionals and self.arch == other.arch
        if using_buildtype:
            optionals = optionals and self.buildtype == other.buildtype
        return optionals

    def equal_or_better(self, other):
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

    def __lt__(self, other):
        return self.version < other.version

    def __hash__(self):
        return hash(self.to_string())

    def dump(self, ret, error, indent='', root=True):
        title = indent + self.to_string()
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
        errors += self.errors
        for dependency in self.dependencies:
            errors += dependency.get_errors(errors)
        return errors

    def add_error(self, error):
        self.errors.append(error)

    def set_lookup(self):
        self.direct_dependency = False
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
            with open(file) as f:
                log.debug('parsing file %s' % file)
                dict = json.loads(f.read())
                package = Package(dict, os.path.dirname(file))
                self.loaded_packages.append(package)

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            log.debug(indent + 'resolving root ' + str(package))
        else:
            log.debug(indent + 'resolving dependency ' + str(package))

        _1 = Indent()

        dependencies = package.get_dependencies()
        package.dependencies = []

        level += 1

        for dependency in dependencies:
            resolved = self.lookup(dependency)
            log.debug(indent + 'will use %s for dependency %s' % (str(resolved), str(dependency)))

            if resolved:
                resolved.parent = package
                resolved = copy.deepcopy(resolved)
                if level > 1:
                    resolved.set_lookup()
                _2 = Indent()
                for d in resolved.get_dependencies():
                    circular_dependency = d.search_upstream()
                    if circular_dependency:
                        resolved.add_error(Error(ErrorCode.CIRCULAR_DEPENDENCY, d, 'required by ' + package.to_string()))
                        package.dependencies.append(resolved)
                        return False
                resolved.set_lookup()
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
        packages = []

        for package in self.loaded_packages:
            packages += self.get_package_list(package)
        unique_packages = set(packages)

        names = [p.get_name() for p in unique_packages]

        names = [name for name, count in collections.Counter(names).items() if count > 1]

        for name in names:
            for package in self.loaded_packages:
                if package.get_name() == name:
                    package.add_error(Error(ErrorCode.MULTIPLE_VERSIONS, package))
                    log.debug("adding multiple version error to %s", package.to_string())

    def get_package_list(self, package, packages=[]):
        packages.append(package)
        for dependency in package.dependencies:
            self.get_package_list(dependency, packages)
        return packages

    def dump_tree(self, root_package):
        ret = []
        error = ErrorCode.OK
        for package in self.loaded_packages:
            if root_package == 'all' or root_package == package.get_name():
                error = package.dump(ret, error)
        return ret, error

    def dump_build_order(self, package_name):
        packages_build_order = []
        packages = []
        for package in self.loaded_packages:
            if package_name == package.get_name() or package_name == "all":
                self.get_package_list(package, packages)
        packages = set(packages)
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

    def get_errors(self, package_name):
        errors = []

        for package in self.loaded_packages:
            if package.get_name() == package_name:

                # first source of errors are those found in the individually copied package objects
                # made to mimic the dependency hierarchy
                errors += package.get_errors()
                dependencies = package.get_dependencies()
                for _package in dependencies:
                    errors += _package.get_errors()

                # second source of errors would be those listed on the loaded packages list directly.
                # (that would currently be multiple version errors).
                used_packages = set(self.get_package_list(package))
                for _package in used_packages:
                    for loaded_package in self.loaded_packages:
                        if loaded_package.get_name() == _package.get_name():
                            errors += loaded_package.get_errors()
                            _package.errors = loaded_package.errors

                return set(errors)

        return ErrorCode.PACKAGE_NOT_FOUND


# ---------------------------------------------------------------------------------------------

obsoleta_root = os.path.dirname(__file__)

def print_error(message):
    print(message)


def print_message(message):
    print(message)


parser = argparse.ArgumentParser('obsoleta')
parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--check', dest='package',
                    help='check specified package recusively')
parser.add_argument('--tree', dest='tree',
                    help='show tree for a package or "all" for all packages')
parser.add_argument('--buildorder', dest='buildorder',
                    help='show dependencies in building order for a package or "all" for all packages')
parser.add_argument('--path', action='store', dest='path',
                    help='comma seperated base path. Use this and/or paths in obsoleta.conf (There are no default path)')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')
parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')


results = parser.parse_args()

if results.verbose:
    log.setLevel(logging.DEBUG)

# parse configuration file

try:
    paths = results.path.split(',')
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
            paths += expanded.split(';')
        using_arch = conf.get('using_arch') == 'on'
        using_track = conf.get('using_track') == 'on'
        using_buildtype = conf.get('using_buildtype') == 'on'
except FileNotFoundError:
    log.info('no configuration file %s found - continuing regardless' % conffile)


paths = [os.path.abspath(p) for p in paths if p]
paths = set(paths)

if not paths:
    log.critical('no paths given from commandline and/or conf file, giving up')
    exit(ErrorCode.MISSING_INPUT.value)

# construct obsoleta, load and parse everything in one go

log.info('searching %i paths' % len(paths))
for path in paths:
    log.info('  path = %s' % path)

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
except Exception as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

exit_code = ErrorCode.UNSET

if not obsoleta.loaded_packages:
    print_error('no packages found, giving up. Searched the path(s):')
    for path in paths:
        print_error('  %s' % path)
    exit_code = ErrorCode.PACKAGE_NOT_FOUND

# and now figure out what to do

elif results.package:
    log.info('checking package "%s"' % results.package)
    errors = obsoleta.get_errors(results.package)
    if errors == ErrorCode.PACKAGE_NOT_FOUND:
        print_error('package "%s" not found' % results.package)
        exit_code = errors
    elif errors:
        print_error('checking package "%s": failed, %i errors found' % (results.package, len(errors)))
        for error in errors:
            print_error('   ' + error.to_string())
            exit_code = error.get_error()
    else:
        print_message('checking package "%s": success' % results.package)
        exit_code = ErrorCode.OK

elif results.buildorder:
    exit_code = ErrorCode.OK
    log.info('packages listed in buildorder')
    unresolved, resolved = obsoleta.dump_build_order(results.buildorder)

    log.info('build order')
    if not resolved:
        print_error(' - unable to find somewhere to start')
    for package in resolved:
        if results.printpaths:
            print_message(package.get_path())
        else:
            print_message(package.to_string())
        errors = package.get_root_error()
        for error in errors:
            exit_code = error.get_error()
            print_error(' - error: ' + error.to_string())

    if unresolved:
        print_error('unable to resolve build order for the following packages (circular dependencies ?)')
        exit_code = ErrorCode.CIRCULAR_DEPENDENCY
        for package in unresolved:
            print_error(' - ' + package.to_string())

elif results.tree:
    log.info('package tree for "%s"' % results.tree)
    dump, error = obsoleta.dump_tree(results.tree)
    if dump:
        print_message("\n".join(dump))
        exit_code = error
    else:
        print_message("package not found")
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

else:
    log.error("no valid command found")


exit(exit_code.value)
