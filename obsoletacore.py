#!/usr/bin/env python3
from log import deb, inf, war, Indent
import os, copy, collections, json
from common import Error, Exceptio
from common import find_in_path
from errorcodes import ErrorCode
from package import Package


class Obsoleta:
    def __init__(self, setup, args):
        self.setup = setup
        self.args = args
        self.dirs_checked = 0
        roots = self.construct_root_list()
        self.package_files = self.find_package_files(roots)
        self.loaded_packages = []

        try:
            if setup.cache:
                try:
                    deb('loading from cache')
                    self.load_cache()
                    return
                except:
                    deb('loading from cache failed')
        except:
            pass

        self.load(self.package_files)

        if not self.loaded_packages:
            raise Exceptio("didn't find any packages", ErrorCode.PACKAGE_NOT_FOUND)

        for package in self.loaded_packages:
            self.resolve_dependencies(package)

        if not self.setup.ignore_duplicates:
            self.check_for_multiple_versions()
        else:
            deb('ignore duplicates, not running "check_for_multiple_versions"')

        inf('package loading and parsing complete with %i errors' % self.get_error_count())

        if setup.cache:
            self.write_cache()

    def construct_root_list(self):
        try:
            roots = self.args.root.split(os.pathsep)
        except:
            roots = []

        try:
            blacklist_paths = self.args.blacklist_paths.split(os.pathsep)
            self.setup.blacklist_paths += blacklist_paths
        except:
            pass
        roots.append(os.getenv('OBSOLETA_ROOT', ''))
        roots += self.setup.paths
        roots = [os.path.abspath(p) for p in roots if p]  # fully qualified non-empty paths
        roots = list(set(roots))  # remove any duplicates

        if not roots:
            roots = '.'
        return roots

    def find_package_files(self, pathlist):
        inf('searching %i paths' % len(pathlist))
        package_files = []
        _ = Indent()
        for path in pathlist:
            inf('path = %s' % path)
            __ = Indent()
            self.dirs_checked = find_in_path(path, 'obsoleta.json', self.setup.depth, package_files)

        inf('= found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        del(_)
        return package_files

    def load(self, json_files):
        json_files = sorted(json_files)
        for file in json_files:
            deb('parsing %s:' % file)
            try:
                multislot_package = Package.is_multislot(file)
            except Exception as e:
                if self.setup.keepgoing:
                    deb('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise Exceptio(file + " '" + str(e) + "'", ErrorCode.BAD_PACKAGE_FILE)

            try:
                if multislot_package:
                    key_files = []
                    path = os.path.dirname(file)
                    find_in_path(path, 'obsoleta.key', 2, key_files)
                    packages = [Package.construct_from_multislot_package_path(self.setup, file, key_file)
                                for key_file in key_files]
                else:
                    packages = [Package.construct_from_package_path(self.setup, file)]

                for package in packages:
                    try:
                        dupe = self.loaded_packages.index(package)
                        message = 'duplicate package %s in %s and %s' % \
                                  (package, package.package_path, self.loaded_packages[dupe].package_path)
                        if self.setup.ignore_duplicates or self.setup.keepgoing:
                            war('ignoring ' + message)
                            if self.args.locate:
                                self.loaded_packages.append(package)
                        else:
                            raise Exceptio(message, ErrorCode.DUPLICATE_PACKAGE)
                    except ValueError:
                        self.loaded_packages.append(package)

            except Exception as e:
                if self.setup.keepgoing:
                    inf('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise e

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            inf('resolving root ' + str(package))
        else:
            inf('resolving dependency ' + str(package))

        _ = Indent()

        dependencies = package.get_dependencies()

        if dependencies:
            package.dependencies = []
            level += 1

            for dependency in dependencies:
                resolved = self.lookup(dependency)

                if resolved:
                    resolved = max(resolved)
                    deb('lookup gave "%s" for dependency %s' % (str(resolved), str(dependency)))
                    _1 = Indent()
                    resolved.parent = package
                    resolved = copy.copy(resolved)
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
                    resolved = copy.copy(dependency)
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
        return candidates

    def locate_upstreams(self, target_package, strict=True):
        candidates = []
        for parent in self.loaded_packages:
            package_deps = parent.get_dependencies()
            if package_deps:
                for package in package_deps:
                    if not strict:
                        if package.equal_or_better(target_package):
                            candidates.append(parent)
                    else:
                        if package == target_package:
                            candidates.append(parent)
        return candidates

    def check_for_multiple_versions(self):
        inf('checking for multiple versions in package tree')
        _ = Indent()

        already_flagged = []

        for package in self.loaded_packages:
            # make a list of package names occurring more than once in the list for 'package'
            package_list = []
            self.get_package_list(package, package_list)
            names = [p.get_name() for p in package_list]
            names = [name for name, count in collections.Counter(names).items() if count > 1]

            for name in names:
                candidates = set()
                for _package in package_list:
                    if _package.get_name() == name:
                        candidates.add(_package)

                for duplicate in candidates:
                    entry = (duplicate, duplicate.parent)
                    if entry not in already_flagged:
                        error = Error(ErrorCode.MULTIPLE_VERSIONS, duplicate, 'with parent %s' % duplicate.parent)
                        duplicate.add_error(error)
                        if self.args.verbose:
                            war(error.to_string())
                        already_flagged.append(entry)

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
        if not found:
            return ret, ErrorCode.PACKAGE_NOT_FOUND
        if found > 1 and root_package.get_name() != '*':
            return ret, ErrorCode.DUPLICATE_PACKAGE
        return ret, error

    def dump_build_order(self, root_package):
        packages_build_order = []
        package_list = []
        for package in self.loaded_packages:
            if package == root_package:
                self.get_package_list(package, package_list)
                break

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
                    loaded_package.error_list_append(errors)
                    package_list = []
                    package_list = set(self.get_package_list(loaded_package, package_list))
                    for _package in package_list:
                        for loaded_package in self.loaded_packages:
                            if loaded_package.get_name() == _package.get_name():
                                loaded_package.error_list_append(errors)
                                _package.errors = loaded_package.errors

                    return list(set(errors))

        return ErrorCode.PACKAGE_NOT_FOUND

    def get_error_count(self):
        errors = 0
        if self.loaded_packages:
            for loaded_package in self.loaded_packages:
                errors += len(loaded_package.error_list_append([]))
        return errors

    def serialize(self):
        return [package.to_dict(True) for package in self.loaded_packages]

    @staticmethod
    def default_cache_filename():
        return os.path.join(os.path.dirname(__file__), 'local/obsoleta.cache')

    def write_cache(self):
        try:
            os.mkdir(os.path.join(os.path.dirname(__file__), 'local'))
        except FileExistsError:
            pass
        packages = self.serialize()
        with open(self.default_cache_filename(), 'w') as f:
            f.write(json.dumps(packages, indent=4))

    def load_cache(self):
        with open(self.default_cache_filename()) as f:
            cache = json.loads(f.read())
        self.loaded_packages = [Package.construct_from_dict(self.setup, p) for p in cache]
