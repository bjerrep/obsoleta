#!/usr/bin/env python3
import json
import argparse
from log import logger as log
from log import inf, deb, cri
from log import Indent as Indent
import logging
import os
import copy
from common import Setup, ErrorCode, Error, NoPackage, print_message, print_value, print_error, find_in_path
from package import Package
import collections


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
        inf('package loading and parsing complete')

    def find_package_files(self, pathlist):
        inf('searching %i paths' % len(pathlist))
        package_files = []
        _ = Indent()
        for path in pathlist:
            inf('path = %s' % path)
            __ = Indent()
            self.dirs_checked = find_in_path(path, 'obsoleta.json', Setup.depth, package_files)

        inf('found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        return package_files

    def load(self, json_files):
        json_files = sorted(json_files)
        for file in json_files:
            try:
                if Package.is_multislot(file):
                    key_files = []
                    path = os.path.dirname(file)
                    find_in_path(path, 'obsoleta.key', 2, key_files)
                    packages = [Package.construct_from_multislot_package_path(file, key_file) for key_file in key_files]
                else:
                    packages = [Package.construct_from_package_path(file)]

                for package in packages:
                    if package in self.loaded_packages:
                        message = 'duplicate package %s in %s' % (package, package.package_path)
                        if Setup.ignore_duplicates:
                            log.warning('ignoring ' + message)
                        else:
                            cri(message, ErrorCode.DUPLICATE_PACKAGE)
                    else:
                        self.loaded_packages.append(package)

            except Exception as e:
                if results.keepgoing:
                    inf('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise e

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            deb('resolving root ' + str(package))
        else:
            deb('resolving dependency ' + str(package))

        _ = Indent()

        dependencies = package.get_dependencies()

        if dependencies:
            package.dependencies = []

            level += 1

            for dependency in dependencies:
                resolved = self.lookup(dependency)
                deb('lookup gave "%s" for dependency %s' % (str(resolved), str(dependency)))

                _ = Indent()

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
                                error = Error(ErrorCode.CIRCULAR_DEPENDENCY, d, 'required by ' + package.to_string())
                                resolved.add_error(error)
                                package.dependencies.append(resolved)
                                return False

                    package.dependencies.append(resolved)
                    self.resolve_dependencies(resolved, level)
                else:
                    resolved = copy.deepcopy(dependency)
                    if level > 1:
                        resolved.set_lookup()
                    error = Error(ErrorCode.PACKAGE_NOT_FOUND, resolved, 'required by ' + package.to_string())
                    resolved.add_error(error)
                    resolved.parent = package
                    package.dependencies.append(resolved)
                    deb('package ' + dependency.to_string() + ' does not exist')

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
        inf('checking for multiple versions in package tree')
        _ = Indent()

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
                            err1 = Error(ErrorCode.MULTIPLE_VERSIONS, candidate[i], 'with parent %s' % candidate[i].parent)
                            log.error('ERROR: ' + err1.to_string())
                            candidate[i].add_error(err1)

                            err2 = Error(ErrorCode.MULTIPLE_VERSIONS, j, 'with parent %s' % j.parent)
                            log.error('ERROR: ' + err2.to_string())
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
        found = 0
        for package in self.loaded_packages:
            if package == root_package:
                found += 1
                error = package.dump(ret, error)
        if found > 1 and root_package.get_name() != '*':
            return ret, ErrorCode.DUPLICATE_PACKAGE
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

parser = argparse.ArgumentParser('obsoleta')
parser.add_argument('--package',
                    help='the package in compact form or "all". See also --path')
parser.add_argument('--path',
                    help='the path for the package. See also --package')
parser.add_argument('--root',
                    help='search root(s), ":" separated. Use this and/or roots in obsoleta.conf (There are no default search path)')
parser.add_argument('--depth',
                    help='search depth relative to root(s). Default 1')
parser.add_argument('--blacklist_paths', action='store',
                    help=': separated list of blacklist substrings')
parser.add_argument('--keepgoing', action='store_true',
                    help='attempt to ignore e.g. packages with otherwise fatal errors')

parser.add_argument('--check', action='store_true',
                    help='command: check a specified package')
parser.add_argument('--tree', action='store_true',
                    help='command: show tree for a package')
parser.add_argument('--buildorder', action='store_true',
                    help='command: show dependencies in building order for a package')
parser.add_argument('--locate', action='store_true',
                    help='command: get the path for the package given with --package')

parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')

parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--verbose', action='store_true',
                    help='enable log messages')


results = parser.parse_args()

if results.verbose:
    log.setLevel(logging.DEBUG)

# go-no-go checks

if not results.package and not results.path:
    print_error('no package specified (use --package for compact form or --path for package dir)')
    exit(ErrorCode.MISSING_INPUT.value)

if not results.tree and not results.check and not results.buildorder and not results.locate:
    print_error('no action specified (use --check, --tree or --buildorder)')
    exit(ErrorCode.MISSING_INPUT.value)

# parse configuration file

conf_paths = Setup.load_configuration(results.conffile)

if results.depth:
    # a depth given on the commandline overrules any depth there might have been in the configuration file
    Setup.depth = int(results.depth)

Setup.dump()

# make the path(s) list

try:
    paths = results.root.split(os.pathsep)
except:
    paths = []

try:
    blacklist_paths = results.blacklist_paths.split(os.pathsep)
except:
    blacklist_paths = []
blacklist_paths += Setup.blacklist_paths

paths += conf_paths
paths = [os.path.abspath(p) for p in paths if p]  # fully qualified non-empty paths
paths = list(set(paths))  # remove any duplicates

if blacklist_paths:
    inf('checking paths against blacklist')
    for path in paths[:]:
        for blacklisted in blacklist_paths:
            if blacklisted in path:
                paths.remove(path)
                inf(' - removing "%s" blacklisted with "%s"' % (path, blacklisted))
                continue

if not paths:
    print_error('no root path(s) specified (use --root and/or config file roots)')
    exit(ErrorCode.MISSING_INPUT.value)


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
except NoPackage:
    print_error('no packages found, giving up. Searched the path(s):')
    for path in paths:
        print_error('  %s' % path)
    exit(ErrorCode.PACKAGE_NOT_FOUND.value)
except Exception as e:
    log.critical('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

exit_code = ErrorCode.UNSET

if results.path:
    try:
        package = Package.construct_from_package_path(results.path)
    except FileNotFoundError as e:
        print_error(str(e))
        exit(ErrorCode.PACKAGE_NOT_FOUND.value)
else:
    package = Package.construct_from_compact(results.package)

# and now figure out what to do

if results.check:
    inf('checking package "%s"' % package)
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
    inf('package tree for "%s"' % package)
    dump, error = obsoleta.dump_tree(package)
    if dump:
        print_message("\n".join(dump))
        exit_code = error
    else:
        print_message("package not found")
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif results.buildorder:
    exit_code = ErrorCode.OK
    inf('packages listed in buildorder')
    unresolved, resolved = obsoleta.dump_build_order(package)

    inf('build order')
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

elif results.locate:
    lookup = obsoleta.lookup(Package.construct_from_compact(results.package))
    if lookup:
        print_value(lookup.get_path())
        exit_code = ErrorCode.OK
    else:
        inf('unable to locate %s' % results.locate)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND
else:
    log.error("no valid command found")

exit(exit_code.value)
