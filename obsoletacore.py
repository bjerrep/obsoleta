#!/usr/bin/env python3
from log import deb, inf, inf_alt, war, err, Indent
from common import Error
import common
from common import find_in_path
from exceptions import PackageNotFound, BadPackageFile, MissingKeyFile, DuplicatePackage
from errorcodes import ErrorCode
from package import Package, anyarch, buildtype_unknown, Track
import os, copy, collections, json, html, datetime


class Obsoleta:
    def __init__(self, setup, args):
        common._setup = setup
        self.setup = setup
        self.args = args
        self.dirs_checked = 0
        self.roots = self.construct_root_list()
        self.package_files = self.find_package_files(self.roots)
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
            raise PackageNotFound("didn't find any packages")

        self.loaded_packages.sort()
        for package in self.loaded_packages:
            if self.resolve_dependencies(package):
                self.aggregate_attributes(package)
            else:
                err('attribute aggregation skipped due to errors in %s' % package.to_string())

        if not self.setup.ignore_duplicates:
            self.check_for_multiple_versions()
        else:
            deb('ignore duplicates, not running "check_for_multiple_versions"')

        inf('loading and parsing complete with %i errors' % self.get_error_count())

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

        del(_)
        inf('found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        return package_files

    def get_duplicates(self, package_list):
        if not package_list:
            return []
        names = [p.get_name() for p in package_list]
        names = [name for name, count in collections.Counter(names).items() if count > 1]
        return names

    def load(self, json_files):
        json_files = sorted(json_files)
        _1 = Indent()
        for file in json_files:
            deb('parsing %s:' % file)
            try:
                try:
                    try:
                        with open(file) as f:
                            _json = f.read()
                            dictionary = json.loads(_json)
                    except json.JSONDecodeError:
                        raise BadPackageFile('malformed json in %s' % file)

                    if dictionary.get('multislot'):
                        key_files = []
                        path = os.path.dirname(file)
                        find_in_path(path, 'obsoleta.key', 2, key_files)
                        packages = [
                            Package.construct_from_package_path(self.setup, file, key_file, dictionary=dictionary)
                            for key_file in key_files]
                    else:
                        packages = [Package.construct_from_package_path(self.setup, file, dictionary=dictionary), ]

                except (BadPackageFile, MissingKeyFile) as e:
                    if self.setup.keepgoing:
                        deb('keep going is set, ignoring invalid package %s' % file)
                    else:
                        raise e

                # multislot packages have more than one package from construction above
                for package in packages:
                    duplicates = self.get_duplicates(package.get_dependencies())
                    if duplicates:
                        raise DuplicatePackage('%s have duplicate packages in its dependency list (%s)' %
                                       (str(package), str(duplicates)))
                    try:
                        dupe = self.loaded_packages.index(package)
                        message = 'duplicate package %s in %s, already exists as %s' % \
                                  (package, package.package_path, self.loaded_packages[dupe].package_path)
                        if self.setup.ignore_duplicates or self.setup.keepgoing:
                            reason = ''
                            if self.setup.ignore_duplicates:
                                reason = ' (ignore duplicates)'
                            if self.setup.keepgoing:
                                reason += ' (keepgoing)'
                            war('ignoring ' + message + reason)
                            if self.args.locate or self.setup.keepgoing:
                                self.loaded_packages.append(package)
                        else:
                            raise DuplicatePackage(message)
                    except ValueError:
                        self.loaded_packages.append(package)

            except Exception as e:
                if self.setup.keepgoing:
                    inf('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise e

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            inf_alt('>resolving ' + str(package))
        else:
            inf('resolving dependency ' + str(package))

        _1 = Indent()

        dependencies = package.get_dependencies()

        if dependencies:
            package.dependencies = []
            level += 1

            for dependency in dependencies:
                errorcode, resolved = self.locate_upstreams(dependency)

                if resolved:
                    resolved = max(resolved)
                    deb('lookup gave "%s" for dependency %s' % (str(resolved), str(dependency)))
                    _2 = Indent()
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
                    dep_success = self.resolve_dependencies(resolved, level)
                    del _2
                    if not dep_success:
                        return False
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

    def aggregate_attributes(self, package, level=0):
        """ Starting from the bottom of the dependency tree then add attributes from upstreams to their
            downstream parent packages in case any downstream attributes are undefined, and the upstream
            attributes are not. (attributes are arch, track and buildtype).
            This will catch illegal situations where e.g. two upstreams have different arch and the downstream
            didn't ask for an explicit arch. If the downstream asked for an explicit arch it would have
            failed while running 'resolve_dependencies'.
            This Aggregate attributes are stored in the 'implicit_attributes' dictionary in a given package.
        """
        dependencies = package.get_dependencies()
        if dependencies:
            _1 = Indent()

            for dependency in dependencies:
                errorcode, resolved_list = self.locate_upstreams(dependency)

                for resolved in resolved_list:
                    if not self.aggregate_attributes(resolved, level):
                        return False

                    # mixing different arch is downright illegal
                    if self.setup.using_arch:
                        resolved_arch = resolved.get_arch(implicit=True)
                        package_arch = package.get_arch(implicit=True)
                        if resolved_arch != anyarch:
                            if package_arch != anyarch and resolved_arch != package_arch:
                                error = Error(
                                    ErrorCode.ARCH_MISMATCH, resolved, 'arch collision with ' + package.to_string())
                                resolved.add_error(error)
                                try:
                                    package.get_dependency(resolved).add_error(error)
                                except:
                                    pass
                                if self.args.verbose:
                                    err(error.to_string())
                                return False
                            else:
                                deb('setting implicit arch for %s to %s' % (package.get_name(), resolved_arch))
                                package.set_implicit('arch', resolved.get_arch())

        return True

    def locate_upstreams(self, target_package):
        """" Find any upstream packages matching 'target_package'
        """
        candidates = []
        for package in self.loaded_packages:
            if package == target_package:
                candidates.append(package)
        if candidates:
            return ErrorCode.OK, candidates

        return ErrorCode.PACKAGE_NOT_FOUND, candidates

    def locate_downstreams(self, target_package):
        """" Find any packages that references the upstream 'target_package' in their
             depends section
        """
        candidates = []
        for parent in self.loaded_packages:
            package_deps = parent.get_dependencies()
            if package_deps:
                for package in package_deps:
                    if package == target_package:
                        candidates.append(parent)
        if candidates:
            return ErrorCode.OK, candidates
        return ErrorCode.PACKAGE_NOT_FOUND, candidates

    def check_for_multiple_versions(self):
        inf('checking for multiple versions in package tree')
        _ = Indent()

        for package in self.loaded_packages:
            package_list = []
            self.get_package_list(package, package_list)
            unique_packages = set(package_list)

            names = self.get_duplicates(unique_packages)

            for name in names:
                candidate = []
                for _package in unique_packages:
                    if _package.get_name() == name:
                        candidate.append(_package)

                for i in range(len(candidate)):
                    for j in candidate[i + 1:]:
                        if candidate[i].is_duplicate(j):
                            err1 = Error(ErrorCode.MULTIPLE_VERSIONS,
                                         candidate[i],
                                         'with parent %s' % candidate[i].parent)
                            candidate[i].add_error(err1)
                            err2 = Error(ErrorCode.MULTIPLE_VERSIONS,
                                         j,
                                         'with parent %s' % j.parent)
                            j.add_error(err2)
                            if self.args.verbose:
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
        if not found:
            return ErrorCode.PACKAGE_NOT_FOUND, ret
        if found > 1 and root_package.get_name() != '*':
            return ErrorCode.PACKAGE_NOT_UNIQUE, ret
        return error, ret

    def dump_build_order(self, root_package):
        packages_build_order = []
        package_list = []
        for package in self.loaded_packages:
            if package == root_package:
                self.get_package_list(package, package_list)
                break

        packages = list(dict.fromkeys(package_list))
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
                nof_dependencies = package.get_nof_dependencies()
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
                        for loaded in self.loaded_packages:
                            if loaded == _package:
                                loaded.error_list_append(errors)
                                _package.errors = loaded.errors

                    if errors:
                        return ErrorCode.DUPLICATE_PACKAGE, list(set(errors))
                    return ErrorCode.OK, errors

        return ErrorCode.PACKAGE_NOT_FOUND, errors

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

    def generate_digraph(self, target_package, dest_file):
        header = '%s[label=<<font face="DejaVuSans" point-size="14"><table border="0" cellborder="0" cellspacing="0">\n'
        title = '<tr><td><font point-size="20"><b>%s</b></font></td></tr>\n'
        specialization = '<tr><td><font color="blue">%s=%s</font></td></tr>\n'
        dependency = '<tr><td><font color="orange">%s=%s</font></td></tr>\n'
        footer = '</table></font>>];\n'

        errorcode, packages = self.locate_upstreams(target_package)
        for package in packages:
            with open(dest_file, 'w') as f:
                f.write('digraph obsoleta {\nnode [shape=plaintext]\n')
                f.write('info[label=<<font face="DejaVuSans" point-size="14">'
                        'Obsoleta dependency graph<br/>%s</font>>];' %
                        datetime.datetime.now().strftime("%Y%m%d %H:%M"))

                def write_package(_package):
                    markup = header % _package.get_name()
                    markup += title % (_package.get_name() + ' - ' + html.escape(str(_package.get_version())))
                    if _package.get_arch() != anyarch:
                        markup += specialization % ('Arch', _package.get_arch())
                    if _package.get_track() != Track.anytrack:
                        markup += specialization % ('Track', _package.get_track())
                    if _package.get_buildtype() != buildtype_unknown:
                        markup += specialization % ('Buildtype', _package.get_buildtype())
                    if _package.get_nof_dependencies():
                        for dep in _package.get_original_dependencies():
                            markup += dependency % ('Depends', html.escape(dep.to_string()))
                    markup += footer
                    f.write('\n' + markup + '\n')

                    if _package.get_nof_dependencies():
                        for dep in _package.get_dependencies():
                            f.write('"%s" -> "%s"\n' % (_package.get_name(), dep.get_name()))
                            _errorcode, _packages = self.locate_upstreams(dep)
                            try:
                                write_package(_packages[0])
                            except:
                                markup = header % (dep.get_name())
                                markup += title % ('Error ' + _package.get_name() + ' - ' +
                                                   html.escape(str(_package.get_version())))
                                markup += footer
                                f.write('\n' + markup + '\n')
                    else:
                        f.write('"%s"\n' % _package.get_name())

                write_package(package)
                f.write('}')
