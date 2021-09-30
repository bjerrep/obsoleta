#!/usr/bin/env python3
from log import deb, inf, inf_alt, inf_alt2, war, err, get_log_level, indent, unindent
from common import Error, ErrorOk, printing_path
from common import find_in_path
from version import Version
from exceptions import PackageNotFound, BadPackageFile, MissingKeyFile, DuplicatePackage
from errorcodes import ErrorCode
from package import Package, anyarch, buildtype_unknown, Track
import os, copy, collections, json, html, datetime, logging
from enum import Enum


class DownstreamFilter(Enum):
    ExplicitReferences = 0
    FollowDownstream = 1
    DownstreamOnly = 2


class Obsoleta:
    def __init__(self, setup, args):
        self.setup = setup
        self.args = args
        self.dirs_checked = 0
        self.roots = self.construct_root_list()
        self.setup.root = min(self.roots, key=len)
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

        if self.setup.allow_duplicates:
            self.check_for_multiple_versions()
        else:
            deb('ignore duplicates, not running "check_for_multiple_versions"')

        inf('loading and parsing complete with %i errors' % self.get_error_count())
        if args.verbose:
            indent()
            for package in self.loaded_packages:
                first_error, errors = self.get_errors(package)
                if errors:
                    err('errors in %s' % (package.to_extra_string()))
                    indent()
                    for error in errors:
                        err(error.print())
                    unindent()
            unindent()

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

        # prepare to remove any duplicate paths, both literally as well as paths already
        # covered by a parent path.
        roots = sorted(roots, key=len)
        to_delete = []

        # in order to complicate things then paths seperated by a distance longer than
        # the current Setup.depth should both be preserved.
        for i in range(len(roots)):
            delete = [root for root in roots[i + 1:] if root.startswith(roots[0])]
            for d in delete:
                difference_path = d.replace(roots[0], '')
                difference_path = difference_path[1:]
                distance = difference_path.count('/')
                if distance < self.setup.depth:
                    to_delete.append(d)

        for delete in to_delete:
            inf('removing duplicate path %s from list of root paths' % delete)
            roots.remove(delete)

        if not roots:
            roots = '.'
        return roots

    def find_package_files(self, roots):
        inf('searching %i roots' % len(roots))
        indent()
        package_files = []
        for root in roots:
            inf('path = %s' % root)
            self.dirs_checked = find_in_path(root, 'obsoleta.json', self.setup.depth, package_files)

        inf('found %i package files in %i directories' % (len(package_files), self.dirs_checked))
        unindent()
        return package_files

    def get_duplicates_by_name(self, package_list):
        if not package_list:
            return []
        names = [p.get_name() for p in package_list]
        names = [name for name, count in collections.Counter(names).items() if count > 1]
        return names

    def dictionary_is_valid(self, dictionary):
        """
        Since the package file can contain all sorts of stuff this helper will decide
        if the dictionary blob is actually obsoleta specific.
        """
        try:
            return dictionary.get('name') or dictionary.get('version') or dictionary.get('arch')
        except:
            return False

    def load(self, json_files):
        json_files = sorted(json_files)
        for file in json_files:
            inf_alt2('loading %s:' % printing_path(file))
            indent()
            try:
                try:
                    try:
                        with open(file) as f:
                            _json = f.read()
                            dictionary = json.loads(_json)
                    except json.JSONDecodeError:
                        raise BadPackageFile('malformed json in %s' % file)

                    if dictionary.get('multislot'):
                        if self.setup.parse_multislot_directly:
                            packages = []
                            for key in dictionary.keys():
                                if key != 'multislot' and self.dictionary_is_valid(dictionary[key]):
                                    packages.append(Package.construct_from_package_path(
                                        self.setup, file, key=key, dictionary=dictionary))
                        else:
                            key_files = []
                            path = os.path.dirname(file)
                            find_in_path(path, 'obsoleta.key', 2, key_files)
                            packages = [
                                Package.construct_from_package_path(
                                    self.setup, file, keypath=key_path, dictionary=dictionary)
                                for key_path in key_files]
                    else:
                        packages = [Package.construct_from_package_path(self.setup, file, dictionary=dictionary), ]

                except (BadPackageFile, MissingKeyFile) as e:
                    if self.setup.keepgoing:
                        war('keep going is set, ignoring invalid package %s' % file)
                        continue
                    else:
                        raise e

                # multislot packages have more than one package from construction above
                for package in packages:
                    duplicates = package.find_equals_no_upgrade(self.loaded_packages)
                    if duplicates:
                        message = ''
                        for duplicate in list([package]) + duplicates:
                            message += ('\n%s\n- located in "%s"' %
                                       (str(duplicate), printing_path(duplicate.get_path())))
                        raise DuplicatePackage(message)

                    dupe = package.find_equals_no_upgrade(self.loaded_packages)
                    if dupe:
                        message = 'duplicate package %s in %s, already exists as %s' % \
                                  (package, package.package_path, dupe[0].package_path)

                        if not self.setup.allow_duplicates or self.setup.keepgoing:
                            reason = ''
                            if not self.setup.allow_duplicates:
                                reason = ' (ignore duplicates)'
                            if self.setup.keepgoing:
                                reason += ' (keepgoing)'
                            war('ignoring ' + message + reason)
                            self.loaded_packages.append(package)
                        else:
                            raise DuplicatePackage(message)
                    else:
                        self.loaded_packages.append(package)

            except Exception as e:
                if self.setup.keepgoing:
                    war('keep going is set, ignoring invalid package %s' % file)
                else:
                    raise e
            unindent()

    def resolve_dependencies(self, package, level=0):
        if level == 0:
            inf_alt('resolving ' + str(package))
        else:
            inf('resolving dependency ' + str(package))

        indent()

        dependencies = package.get_dependencies()

        if dependencies:
            package.dependencies = []
            level += 1

            for dependency in dependencies:
                errorcode, resolved = self.find_all_dependencies(dependency)

                if resolved:
                    resolved = max(resolved)
                    deb('lookup gave "%s" for dependency %s' % (str(resolved), str(dependency)))
                    indent()
                    resolved.parent = package
                    resolved = copy.copy(resolved)
                    if level > 1:
                        resolved.set_lookup()
                    resolved_dependencies = resolved.get_dependencies()
                    if resolved_dependencies:
                        for d in resolved_dependencies:
                            circular_dependency = d.search_upstream()
                            if circular_dependency:
                                error = Error(ErrorCode.CIRCULAR_DEPENDENCY, d,
                                              d.to_string() + ' required by ' + package.to_string())
                                resolved.add_error(error)
                                package.dependencies.append(resolved)
                                return False

                    package.dependencies.append(resolved)
                    dep_success = self.resolve_dependencies(resolved, level)
                    unindent()
                    if not dep_success:
                        return False
                else:
                    resolved = copy.copy(dependency)
                    if level > 1:
                        resolved.set_lookup()
                    error = Error(ErrorCode.PACKAGE_NOT_FOUND, resolved,
                                  resolved.to_string() + ' required by ' + package.to_string())
                    resolved.add_error(error)
                    resolved.parent = package
                    package.dependencies.append(resolved)
                    if get_log_level() <= logging.INFO:
                        war('package ' + dependency.to_string() + ' does not exist, required by ' + package.to_string())

            level -= 1
        unindent()
        return True

    def aggregate_attributes(self, package, level=0):
        """
        Starting from the bottom of the dependency tree then add attributes from upstreams to their
        downstream parent packages in case any downstream attributes are undefined, and the upstream
        attributes are not. (attributes are arch, track and buildtype).
        This will catch illegal situations where e.g. two upstreams have different arch and the downstream
        didn't ask for an explicit arch. If the downstream asked for an explicit arch it would have
        failed while running 'resolve_dependencies'.
        This Aggregate attributes are stored in the 'implicit_attributes' dictionary in a given package.
        """
        dependencies = package.get_dependencies()
        if dependencies:
            indent()

            for dependency in dependencies:
                errorcode, resolved_list = self.find_all_dependencies(dependency)

                for resolved in resolved_list:
                    if not self.aggregate_attributes(resolved, level):
                        return False

                    # mixing different arch is downright illegal
                    if self.setup.using_arch:
                        resolved_arch = resolved.get_arch(implicit=True)
                        package_arch = package.get_arch(implicit=True)

                        if resolved_arch != anyarch and resolved_arch != package_arch:
                            if package_arch != anyarch:
                                error = Error(
                                    ErrorCode.ARCH_MISMATCH, resolved, 'arch collision with ' + package.to_string())
                                resolved.add_error(error)
                                try:
                                    package.find_dependency(resolved, strict=True).add_error(error)
                                except:
                                    pass
                                if self.args.verbose:
                                    err(error.to_string())
                                return False
                            else:
                                deb('setting implicit arch for %s to %s' % (package.get_name(), resolved_arch))
                                package.set_implicit('arch', resolved.get_arch())
            unindent()

        return True

    def locate_external_lib(self, target_package):
        try:
            so_path = target_package.get_value('so')
            name = target_package.get_value('name')
            lib_name = 'lib%s.so' % name
            so = os.path.join(so_path, lib_name)

            binary = os.readlink(so)
            version = binary. replace(lib_name + '.', '')
            _ = Version(version)
            package = Package.construct_from_compact(self.setup, '%s:%s' % (name, version), so_path)
            self.loaded_packages.append(package)
            return [package]
        except:
            return []

    def find_all_dependencies(self, target_package):
        """
        Find dependencies, either as native obsoleta packages or external libraries.
        Prefer perfect hits but if none is found then look for 'equal or better' packages.
        """
        candidates = target_package.find_equals_no_upgrade(self.loaded_packages)

        if not candidates:
            for package in self.loaded_packages:
                if self.setup.keep_track or target_package.keep_track:
                    if package.package_is_equal_or_better(target_package):
                        candidates.append(package)
                elif package.package_is_equal_or_better_relaxed_track(target_package):
                    candidates.append(package)

        if not candidates:
            candidates = self.locate_external_lib(target_package)

        if candidates:
            return ErrorOk(), candidates

        return Error(ErrorCode.PACKAGE_NOT_FOUND,
                     target_package,
                     'no upstreams matches %s' % target_package.to_string()), candidates

    def find_all_packages(self, package):
        matches = package.find_equal_or_better_in_list(self.loaded_packages)

        if not matches:
            return Error(ErrorCode.PACKAGE_NOT_FOUND, package), matches

        return ErrorOk(), matches

    def find_first_package(self, package, strict=False):
        """
        Return the package requested. If strict is True it is an error if more than one
        is found, otherwise just the first found is returned.
        """
        error, matches = self.find_all_packages(package)

        if error.has_error():
            return error, []

        if len(matches) > 1:
            if strict:
                ret = []
                for _package in matches:
                    error = _package.dump(ret, error, skip_dependencies=True)
                message = 'Package "%s", candidates are %s' % (package, str(ret))
                return Error(ErrorCode.PACKAGE_NOT_UNIQUE, _package, message), matches
            else:
                inf('find_any=True: returning %s but other candidates were %s' % (matches[0], matches[1:]))

        return ErrorOk(), matches[0]

    def get_all_archs(self):
        archs = []
        for package in self.loaded_packages:
            archs.append(package.get_arch())
        return list(set(archs))

    def locate_upstreams(self, target_package, full_tree=False, candidates=None):
        """"
        Resolve all upstream packages listed in the 'target_package' depends section
        in case full_tree is the default False, and if full tree is True, then resolve all dependencies
        recursively.
        Returns tupple (error, list of the resolved packages).
        If all packages were resolved then error will contain ErrorCode.OK.
        """
        if candidates is None:
            candidates = []

        error, target = self.find_first_package(target_package)
        if error.has_error():
            return error, target

        dependencies = target.get_dependencies()
        if not dependencies:
            return ErrorOk(), candidates

        for upstream in dependencies:
            if full_tree:
                error, candidates = self.locate_upstreams(upstream, full_tree, candidates)
                if error.has_error():
                    return error, candidates
                candidates.append(upstream)
            else:
                error, found = self.find_first_package(upstream)
                if found:
                    candidates.append(found)
                else:
                    err = Error(ErrorCode.PACKAGE_NOT_FOUND,
                                target,
                                "no upstream %s found for %s" % (upstream, target))
                    return err, candidates
        return ErrorOk(), candidates

    def locate_downstreams(self, target_package, downstream_filter, downstream_packages=None):
        """
        Find any downstream packages that references the 'target_package' in their
        depends section
        """
        if downstream_packages is None:
            downstream_packages = []

        for parent in self.loaded_packages:
            package_deps = parent.get_dependencies()
            if package_deps:
                for package in package_deps:
                    if package == target_package:
                        if (downstream_filter != DownstreamFilter.DownstreamOnly or
                                not parent.parent):
                            downstream_packages.append(parent)
                        if (downstream_filter == DownstreamFilter.FollowDownstream or
                                downstream_filter == DownstreamFilter.DownstreamOnly):
                            self.locate_downstreams(parent,
                                                    downstream_filter=downstream_filter,
                                                    downstream_packages=downstream_packages)

        if downstream_packages:
            return ErrorOk(), downstream_packages
        return Error(ErrorCode.PACKAGE_NOT_FOUND,
                     target_package,
                     "%s not found" % target_package), downstream_packages

    def check_for_multiple_versions(self):
        inf('checking for multiple versions in package tree')
        indent()

        for package in self.loaded_packages:
            package_list = []
            self.get_package_list(package, package_list)
            unique_packages = set(package_list)

            names = self.get_duplicates_by_name(unique_packages)

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
        unindent()

    def get_package_list(self, package, packages):
        packages.append(package)
        if package.dependencies:
            for dependency in package.dependencies:
                self.get_package_list(dependency, packages)
        return packages

    def dump_tree(self, root_package):
        """
        Return a list of all package compactpyt names in the root_package tree.
        If there are multiple candidates found it is flagged as an error and the list
        will contain only the possible candidates preventing a unique match.
        If there are no errors then the list will contain a full recursive dump with
        indention for dependencies matching their depth in the tree.
        """
        ret = []
        error = ErrorOk()

        matches = root_package.find_equal_or_better_in_list(self.loaded_packages)

        if not matches:
            return Error(ErrorCode.PACKAGE_NOT_FOUND, root_package), ret

        if len(matches) > 1 and root_package.get_name() != '*':
            for package in matches:
                error = package.dump(ret, error, skip_dependencies=True)
            message = 'Package "%s", candidates are %s' % (root_package, str(ret))
            return Error(ErrorCode.PACKAGE_NOT_UNIQUE, root_package, message), ret

        for package in matches:
            error = package.dump(ret, error, skip_dependencies=False)
        return error, ret

    def dump_build_order(self, root_package):
        packages_build_order = []
        package_list = []

        error, match = self.find_first_package(root_package)
        if error.has_error():
            return error, match, []

        self.get_package_list(match, package_list)

        packages = list(dict.fromkeys(package_list))
        package_copy = packages

        if package_list:
            deleted = []
            found_next = True

            while found_next:
                found_next = False
                for package in package_copy:
                    upstreams = package.get_nof_dependencies()
                    if not upstreams:
                        packages_build_order.append(package)
                        package_copy.remove(package)
                        deleted.append(package)
                        found_next = True
                        break

                    for dp in package.get_dependencies():
                        if dp in deleted:
                            upstreams -= 1
                    if not upstreams:
                        packages_build_order.append(package)
                        package_copy.remove(package)
                        deleted.append(package)
                        found_next = True
                        break
            if not packages_build_order:
                error = Error(ErrorCode.CIRCULAR_DEPENDENCY, root_package, 'can\'t resolve %s' % root_package)
        else:
            error = Error(ErrorCode.RESOLVE_ERROR, root_package, '%s not found' % root_package)

        if not error:
            error = ErrorOk()
        return error, package_copy, packages_build_order

    def get_errors(self, package, errors=None):
        if errors is None:
            errors = []
        anypackage = package.get_name() == '*'
        if not self.loaded_packages or (not anypackage and not package.find_equal_or_better_in_list(self.loaded_packages)):
            return Error(ErrorCode.PACKAGE_NOT_FOUND, package), errors

        if not package:
            for _package in self.loaded_packages:
                _package.error_list_append(_package, errors)
            if errors:
                return errors[0], list(set(errors))
            return ErrorOk(), errors

        if anypackage:
            for _package in self.loaded_packages:
                _package.error_list_append(errors)
        else:
            package = package.find_equal_or_better_in_list(self.loaded_packages)[0]
            package.error_list_append(errors)

        if errors:
            errors = sorted(list(set(errors)))
        return ErrorOk(), errors

    def get_error_count(self):
        errors = 0
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

    def generate_digraph(self, target_package):
        header = '%s[label=<<font face="DejaVuSans" point-size="14"><table border="0" cellborder="0" cellspacing="0">\n'
        title = '<tr><td><font point-size="20"><b>%s</b></font></td></tr>\n'
        specialization = '<tr><td><font color="blue">%s=%s</font></td></tr>\n'
        specialization_msg = '<tr><td><font color="blue">%s</font></td></tr>\n'
        dependency = '<tr><td><font color="orange">%s=%s</font></td></tr>\n'
        footer = '</table></font>>];\n'

        errorcode, packages = self.find_all_dependencies(target_package)
        for package in packages:
            dest_file = package.to_compact_string('_', True) + '.gv'
            inf('generating digraph for %s as %s' % (package, dest_file))
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
                        for dep in _package.get_dependencies():
                            markup += dependency % ('Depends', html.escape(dep.to_string()))
                    markup += footer
                    f.write('\n' + markup + '\n')

                    if _package.get_nof_dependencies():
                        for dep in _package.get_dependencies():
                            f.write('"%s" -> "%s"\n' % (_package.get_name(), dep.get_name()))
                            _errorcode, _packages = self.find_all_dependencies(dep)
                            try:
                                write_package(_packages[0])
                            except:
                                markup = header % (dep.get_name())
                                markup += title % ('Error ' + dep.get_name() + ' - ' +
                                                   html.escape(str(dep.get_version())))
                                markup += specialization_msg % dep.get_root_error()
                                markup += footer
                                f.write('\n' + markup + '\n')
                    else:
                        f.write('"%s"\n' % _package.get_name())

                write_package(package)
                f.write('}')
