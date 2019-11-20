#!/usr/bin/env python3
import argparse
from log import logger as log
from log import inf, deb, err
from log import Indent as Indent
import logging, os, copy
from common import Setup, Error, Exceptio
from common import find_in_path
from errorcodes import ErrorCode
from package import Package
import collections
import traceback


class Obsoleta:
    def __init__(self, paths):
        self.dirs_checked = 0
        self.base_paths = paths
        self.package_files = self.find_package_files(paths)

        self.loaded_packages = []
        self.load(self.package_files)

        if not self.loaded_packages:
            raise Exceptio("didn't find any packages", ErrorCode.PACKAGE_NOT_FOUND)

        for package in self.loaded_packages:
            self.resolve_dependencies(package)

        if not Setup.ignore_duplicates:
            self.check_for_multiple_versions()
        else:
            deb('ignore duplicates, not running "check_for_multiple_versions"')
        deb('package loading and parsing complete')

    def find_package_files(self, pathlist):
        deb('searching %i paths' % len(pathlist))
        package_files = []
        _ = Indent()
        for path in pathlist:
            deb('path = %s' % path)
            __ = Indent()
            self.dirs_checked = find_in_path(path, 'obsoleta.json', Setup.depth, package_files)

        deb('= found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        del(_)
        return package_files

    def load(self, json_files):
        json_files = sorted(json_files)
        for file in json_files:
            try:
                multislot_package = Package.is_multislot(file)
            except Exception as e:
                if results.keepgoing:
                    deb('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise Exceptio(file + " '" + str(e) + "'", ErrorCode.BAD_PACKAGE_FILE)

            try:
                if multislot_package:
                    key_files = []
                    path = os.path.dirname(file)
                    find_in_path(path, 'obsoleta.key', 2, key_files)
                    packages = [Package.construct_from_multislot_package_path(file, key_file) for key_file in key_files]
                else:
                    packages = [Package.construct_from_package_path(file)]

                for package in packages:
                    if package in self.loaded_packages:
                        message = 'duplicate package %s in %s' % (package, package.package_path)
                        if Setup.ignore_duplicates or results.keepgoing:
                            log.warning('ignoring ' + message)
                            if results.locate:
                                self.loaded_packages.append(package)
                        else:
                            raise Exceptio(message, ErrorCode.DUPLICATE_PACKAGE)
                    else:
                        self.loaded_packages.append(package)

            except Exception as e:
                if results.keepgoing:
                    deb('keep going is set, ignoring invalid package %s' % file)
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

    def lookup(self, target_package, strict=False):
        candidates = []
        for package in self.loaded_packages:
            if not strict:
                if package.equal_or_better(target_package):
                    candidates.append(package)
            else:
                if package == target_package:
                    candidates.append(package)
        if not candidates:
            return None
        return max(candidates)

    def check_for_multiple_versions(self):
        deb('checking for multiple versions in package tree')
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
                            candidate[i].add_error(err1)
                            err2 = Error(ErrorCode.MULTIPLE_VERSIONS, j, 'with parent %s' % j.parent)
                            j.add_error(err2)
                            if results.verbose:
                                err('ERROR: ' + err1.to_string())
                                err('ERROR: ' + err2.to_string())

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
    err('no package specified (use --package for compact form or --path for package dir)')
    exit(ErrorCode.MISSING_INPUT.value)

if not results.tree and not results.check and not results.buildorder and not results.locate:
    err('no action specified (use --check, --tree or --buildorder)')
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
    Setup.blacklist_paths += blacklist_paths
except:
    pass

paths += conf_paths
paths = [os.path.abspath(p) for p in paths if p]  # fully qualified non-empty paths
paths = list(set(paths))  # remove any duplicates

if not paths:
    paths = '.'

# construct obsoleta, load and parse everything in one go

try:
    obsoleta = Obsoleta(paths)

    if results.path:
        try:
            package = Package.construct_from_package_path(results.path)
        except FileNotFoundError as e:
            err(str(e))
            exit(ErrorCode.PACKAGE_NOT_FOUND.value)
    else:
        package = Package.construct_from_compact(results.package)

except Exceptio as e:
    log.critical(str(e))
    log.critical(ErrorCode.to_string(e.ErrorCode.value))
    exit(e.ErrorCode.value)
except Exception as e:
    log.critical('caught unexpected exception: %s' % str(e))
    if results.verbose:
        print(traceback.format_exc())
    exit(ErrorCode.UNKNOWN_EXCEPTION.value)

exit_code = ErrorCode.UNSET

# and now figure out what to do

if results.check:
    deb('checking package "%s"' % package)
    errors = obsoleta.get_errors(package)

    if errors == ErrorCode.PACKAGE_NOT_FOUND:
        err('package "%s" not found' % package)
        exit_code = errors
    elif errors:
        err('checking package "%s": failed, %i errors found' % (package, len(errors)))
        for error in errors:
            err('   ' + error.to_string())
            exit_code = error.get_error()
    else:
        inf('checking package "%s": success' % package)
        exit_code = ErrorCode.OK

elif results.tree:
    inf('package tree for "%s"' % package)
    dump, error = obsoleta.dump_tree(package)
    if dump:
        inf("\n".join(dump))
        exit_code = error
    else:
        inf("package '%s'not found" % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif results.buildorder:
    exit_code = ErrorCode.OK
    deb('packages listed in buildorder')
    unresolved, resolved = obsoleta.dump_build_order(package)

    if not resolved:
        err(' - unable to find somewhere to start')

    for _package in resolved:
        if results.printpaths:
            package_path = _package.get_path()
            if package_path:
                inf(package_path)
            else:
                inf(_package.to_string())
        else:
            inf(_package.to_string())

        errors = _package.get_root_error()
        if errors:
            for error in errors:
                exit_code = error.get_error()
                err(' - error: ' + error.to_string())

    if unresolved:
        err('unable to resolve build order for the following packages (circular dependencies ?)')
        exit_code = ErrorCode.CIRCULAR_DEPENDENCY
        for _package in unresolved:
            err(' - ' + _package.to_string())

elif results.locate:
    lookup = obsoleta.lookup(package, strict=True)
    if lookup:
        inf(lookup.get_path())
        exit_code = ErrorCode.OK
    else:
        inf('unable to locate %s' % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND
else:
    log.error("no valid command found")

exit(exit_code.value)
