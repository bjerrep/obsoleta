#!/usr/bin/env python3
import os, copy, collections, json, html, datetime
from enum import Enum
from log import deb, inf, inf_alt, inf_alt2, war, err, get_info_log_level, indent, unindent
from common import Error, ErrorOk, printing_path
from common import find_in_path
from version import Version
from exceptions import PackageNotFound, BadPackageFile, MissingKeyFile, DuplicatePackage
from errorcodes import ErrorCode
from package import Package, anyarch, buildtype_unknown, Track


class UpDownstreamFilter(Enum):
    ExplicitReferences = 0
    FollowTree = 1
    TreeOnly = 2


class Obsoleta:
    def __init__(self, conf, args):
        self.conf = conf
        self.args = args
        self.dirs_checked = 0
        self.roots = self.construct_root_list()
        self.conf.root = min(self.roots, key=len)
        self.package_files = self.find_package_files(self.roots)
        self.loaded_packages = []

        try:
            if conf.cache:
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
                err(f'attribute aggregation skipped due to errors in {package.to_string()}')

        if not self.conf.allow_duplicates:
            self.check_for_multiple_versions()
        else:
            deb('ignore duplicates, not running "check_for_multiple_versions"')

        inf(f'loading and parsing complete with {self.get_error_count()} errors')
        if args.verbose:
            indent()
            for package in self.loaded_packages:
                _, errors = self.get_errors(package)
                if errors:
                    err(f'errors in {package.to_extra_string()}')
                    indent()
                    for error in errors:
                        err(error.print())
                    unindent()
            unindent()

        if conf.cache:
            self.write_cache()

    def construct_root_list(self):
        try:
            roots = self.args.root.split(os.pathsep)
        except:
            roots = []

        try:
            blacklist_paths = self.args.blacklist_paths.split(os.pathsep)
            self.conf.blacklist_paths += blacklist_paths
        except:
            pass
        roots.append(os.getenv('OBSOLETA_ROOT', ''))
        roots += self.conf.paths
        roots = [os.path.abspath(p) for p in roots if p]  # fully qualified non-empty paths

        # prepare to remove any duplicate paths, both literally as well as paths already
        # covered by a parent path.
        roots = sorted(roots, key=len)
        to_delete = []

        # in order to complicate things then paths seperated by a distance longer than
        # the current Conf.depth should both be preserved.
        for i in range(len(roots)):
            delete = [root for root in roots[i + 1:] if root.startswith(roots[0])]
            for d in delete:
                difference_path = d.replace(roots[0], '')
                difference_path = difference_path[1:]
                distance = difference_path.count('/')
                if distance < self.conf.depth:
                    to_delete.append(d)

        for delete in to_delete:
            inf(f'removing duplicate path {delete} from list of root paths')
            roots.remove(delete)

        if not roots:
            roots = '.'
        return roots

    def find_package_files(self, roots):
        inf('searching %i roots' % len(roots))
        indent()
        package_files = []
        for root in roots:
            inf(f'path = {root}')
            self.dirs_checked = find_in_path(root, 'obsoleta.json', self.conf.depth, package_files)

        inf(f'found {len(package_files)} package files in {self.dirs_checked} directories')
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
            inf_alt2(f'loading {printing_path(file)}:')
            indent()
            try:
                try:
                    try:
                        with open(file) as f:
                            _json = f.read()
                            dictionary = json.loads(_json)
                    except json.JSONDecodeError:
                        raise BadPackageFile(f'malformed json in {file}')

                    if dictionary.get('multislot'):
                        if self.conf.parse_multislot_directly:
                            packages = []
                            for key in dictionary.keys():
                                if key != 'multislot' and self.dictionary_is_valid(dictionary[key]):
                                    packages.append(Package.construct_from_package_path(
                                        self.conf, file, key=key, dictionary=dictionary))
                        else:
                            key_files = []
                            path = os.path.dirname(file)
                            find_in_path(path, 'obsoleta.key', 2, key_files)
                            packages = [
                                Package.construct_from_package_path(
                                    self.conf, file, keypath=key_path, dictionary=dictionary)
                                for key_path in key_files]
                    else:
                        packages = [Package.construct_from_package_path(self.conf, file, dictionary=dictionary), ]

                except (BadPackageFile, MissingKeyFile) as e:
                    if self.conf.keepgoing:
                        war('keep going is set, ignoring invalid package %s' % file)
                        continue
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

                        if not self.conf.allow_duplicates or self.conf.keepgoing:
                            reason = ''
                            if not self.conf.allow_duplicates:
                                reason = ' (ignore duplicates)'
                            if self.conf.keepgoing:
                                reason += ' (keepgoing)'
                            war('ignoring ' + message + reason)
                            self.loaded_packages.append(package)
                        else:
                            raise DuplicatePackage(message)
                    else:
                        self.loaded_packages.append(package)

            except Exception as e:
                if self.conf.keepgoing:
                    war(f'keep going is set, ignoring invalid package {file}')
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
                _, dependency_dependencies = self.find_all_dependencies(dependency)

                if dependency_dependencies:
                    for resolved in dependency_dependencies:
                        deb(f'lookup gave "{str(resolved)}" for dependency {str(dependency)}')

                        resolved.parent = package
                        resolved = copy.copy(resolved)
                        if level > 1:
                            resolved.set_lookup()
                        resolved_dependencies = resolved.get_dependencies()
                        if resolved_dependencies:
                            for d in resolved_dependencies:
                                circular_dependency = d.search_upstream()

                                if circular_dependency:
                                    _error, loaded_package = self.find_first_package(d)

                                    if loaded_package.get_errors():
                                        continue
                                    error = Error(ErrorCode.CIRCULAR_DEPENDENCY, d,
                                                  d.to_string() + ' required by ' + resolved.to_extra_string())
                                    if _error.is_ok():
                                        loaded_package.add_error(error)
                                    package.dependencies.append(resolved)
                                    return False

                        dep_success = self.resolve_dependencies(resolved, level)
                        unindent()
                        if not dep_success:
                            return False

                    selected_dependency = max(dependency_dependencies)
                    package.dependencies.append(selected_dependency)
                else:
                    resolved = copy.copy(dependency)
                    if level > 1:
                        resolved.set_lookup()
                    error = Error(ErrorCode.PACKAGE_NOT_FOUND, resolved,
                                  resolved.to_string() + ' required by ' + package.to_string())
                    resolved.add_error(error)
                    resolved.parent = package
                    package.dependencies.append(resolved)
                    if get_info_log_level():
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
                _errorcode, resolved_list = self.find_all_dependencies(dependency)

                for resolved in resolved_list:
                    if not self.aggregate_attributes(resolved, level):
                        return False

                    # mixing different arch is downright illegal
                    if self.conf.using_arch:
                        resolved_arch = resolved.get_arch(implicit=True)
                        package_arch = package.get_arch(implicit=True)

                        if resolved_arch not in (anyarch, package_arch):
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

                            deb(f'setting implicit arch for {package.get_name()} to {resolved_arch}')
                            package.set_implicit('arch', resolved.get_arch())
            unindent()

        return True

    def locate_external_lib(self, target_package):
        try:
            so_path = target_package.get_value('so')
            name = target_package.get_value('name')
            lib_name = f'lib{name}.so'
            so = os.path.join(so_path, lib_name)

            binary = os.readlink(so)
            version = binary. replace(lib_name + '.', '')
            _ = Version(version)
            package = Package.construct_from_compact(self.conf, '%s:%s' % (name, version), so_path)
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
                if self.conf.keep_track or target_package.keep_track:
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
        Return tupple (error if any, the first package matching 'package').
        If strict is True it is itself an error if more than one candidate is found.
        """
        error, matches = self.find_all_packages(package)

        if error.has_error():
            return error, []

        if len(matches) > 1:
            if strict:
                ret = []
                for _package in matches:
                    _package.dump(ret, skip_dependencies=True)
                message = f'Package "{package}", candidates are {str(ret)}'
                return Error(ErrorCode.PACKAGE_NOT_UNIQUE, _package, message), matches

            inf(f'multiple candidates found but strict=False, returning {matches[0]} but other candidates were {matches[1:]}')

        return ErrorOk(), matches[0]

    def get_all_archs(self):
        archs = []
        for package in self.loaded_packages:
            archs.append(package.get_arch())
        return list(set(archs))

    def get_archs(self, package):
        error, targets = self.find_all_packages(package)
        if error.has_error():
            return error, package

        archs = []
        for target in targets:
            archs.append(target.get_arch())
        return ErrorOk(), list(set(archs))

    def locate_upstreams(self, target_package, updown_stream_filter, upstream_packages=None):
        """"
        Find any upstream packages that the 'target_package' references.
        Param: 'updown_stream_filter' of type UpDownstreamFilter (specifying the depth)
        Returns: tuple(errorcode, [upstream packages])
        """
        if upstream_packages is None:
            upstream_packages = []
            error, package = self.find_first_package(target_package, strict=True)
            if not package:
                return Error(ErrorCode.PACKAGE_NOT_FOUND,
                             target_package,
                             f'{target_package} not found'), upstream_packages

        error, target = self.find_first_package(target_package)
        if error.has_error():
            return error, target

        dependencies = target.get_dependencies()

        for upstream in dependencies:
            if updown_stream_filter == UpDownstreamFilter.FollowTree:
                error, candidates = self.locate_upstreams(upstream,
                                                          updown_stream_filter=updown_stream_filter,
                                                          upstream_packages=upstream_packages)
                if error.has_error():
                    return error, candidates
                upstream_packages.append(upstream)
            else:
                error, found = self.find_first_package(upstream)
                if found:
                    upstream_packages.append(found)
                else:
                    error = Error(ErrorCode.PACKAGE_NOT_FOUND,
                                target,
                                "no upstream %s found for %s" % (upstream, target))
                    return error, upstream_packages

        upstreams = sorted(list(set(upstream_packages)))
        if not upstreams:
            inf(f'no upstreams found for {target_package}')
        return ErrorOk(), upstreams

    def locate_downstreams(self, target_package, updown_stream_filter, downstream_packages=None):
        """
        Find any downstream packages that references the 'target_package' in their
        depends section.
        Param: 'updown_stream_filter' of type UpDownstreamFilter (specifying the depth)
        Returns: tuple(errorcode, [downstream packages])
        """
        if downstream_packages is None:
            downstream_packages = []
            _error, package = self.find_first_package(target_package, strict=True)
            if not package:
                return Error(ErrorCode.PACKAGE_NOT_FOUND,
                             target_package,
                             f'{target_package} not found'), downstream_packages

        for parent in self.loaded_packages:
            package_deps = parent.get_dependencies()
            if package_deps:
                for package in package_deps:
                    if package.package_is_equal_or_better(target_package, strict_track=False):
                        if updown_stream_filter != UpDownstreamFilter.TreeOnly or not parent.parent:
                            downstream_packages.append(parent)
                        if updown_stream_filter in (UpDownstreamFilter.FollowTree, UpDownstreamFilter.TreeOnly):
                            self.locate_downstreams(parent,
                                                    updown_stream_filter=updown_stream_filter,
                                                    downstream_packages=downstream_packages)

        if not downstream_packages:
            inf(f'no downstreams found for {target_package}')
        return ErrorOk(), sorted(list(set(downstream_packages)))

    def check_for_multiple_versions(self):
        inf('checking for multiple versions in package tree')
        indent()

        for package in self.loaded_packages:
            package_list = self.get_package_list(package)
            unique_packages = set(package_list)

            names = self.get_duplicates_by_name(unique_packages)

            for name in names:
                candidate = []
                for _package in unique_packages:
                    if _package.get_name() == name:
                        candidate.append(_package)

                for i in range(len(candidate)):
                    for second_candidate in candidate[i + 1:]:
                        if candidate[i].is_duplicate(second_candidate):
                            err1 = Error(ErrorCode.MULTIPLE_VERSIONS,
                                         candidate[i],
                                         f'with parent {candidate[i].parent}')
                            err2 = Error(ErrorCode.MULTIPLE_VERSIONS,
                                         second_candidate,
                                         f'with parent {second_candidate.parent}')
                            package.add_error(err1)
                            package.add_error(err2)
                            if self.args.verbose:
                                err('ERROR: ' + err1.to_string())
                                err('ERROR: ' + err2.to_string())
        unindent()

    def get_package_list(self, package, packages=None):
        if packages is None:
            packages = []
        packages.append(package)
        if package.dependencies:
            for dependency in package.dependencies:
                packages.extend(self.get_package_list(dependency))
        return packages

    def dump_tree(self, root_package):
        """
        Return tupple (first error found or ErrorOk, list of all package compact names in the root_package tree)
        If there are multiple candidates found it is flagged as an error and the list
        will contain only the possible candidates preventing a unique match.
        If there are no errors then the list will contain a full recursive dump with
        indention for dependencies matching their depth in the tree.
        """
        ret = []

        matches = root_package.find_equal_or_better_in_list(self.loaded_packages)

        if not matches:
            return Error(ErrorCode.PACKAGE_NOT_FOUND, root_package), ret

        if len(matches) > 1 and root_package.get_name() != '*':
            for package in matches:
                package.dump(ret, skip_dependencies=True)
            message = 'Package "%s", candidates are %s' % (root_package, str(ret))
            return Error(ErrorCode.PACKAGE_NOT_UNIQUE, root_package, message), ret

        for package in matches:
            errors, _ = package.dump(ret, skip_dependencies=False)
            if errors:
                return errors[0], ret

        return ErrorOk(), ret

    def dump_build_order(self, root_package):
        """
        Returns a tupple (error, [upstreams sorted in build order])
        """
        packages_build_order = []

        error, match = self.find_first_package(root_package)
        if error.has_error():
            return error, []

        if match.get_errors():
            return match.get_errors()[0], []

        package_list = self.get_package_list(match)

        if package_list:
            deleted = []
            found_next = True

            while found_next:
                found_next = False
                for package in package_list.copy():
                    upstreams = package.get_nof_dependencies()
                    if not upstreams:
                        packages_build_order.append(package)
                        package_list.remove(package)
                        deleted.append(package)
                        found_next = True
                        break

                    for dp in package.get_dependencies():
                        if dp in deleted:
                            upstreams -= 1
                    if not upstreams:
                        packages_build_order.append(package)
                        package_list.remove(package)
                        deleted.append(package)
                        found_next = True
                        break

            if not packages_build_order:
                error = Error(ErrorCode.CIRCULAR_DEPENDENCY, root_package, 'can\'t resolve %s' % root_package)
            if package_list:
                return Error(ErrorCode.RESOLVE_ERROR,
                             root_package,
                             f'unable to fully resolve {root_package}'), packages_build_order
        else:
            error = Error(ErrorCode.RESOLVE_ERROR, root_package, '%s not found' % root_package)

        if not error:
            error = ErrorOk()
        return error, packages_build_order

    def get_errors(self, package, errors=None):
        if errors is None:
            errors = []
        anypackage = package.get_name() == '*'

        if (not self.loaded_packages or
           (not anypackage and not package.find_equal_or_better_in_list(self.loaded_packages))):
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
            return Error(ErrorCode.RESOLVE_ERROR, package), errors
        return ErrorOk(), []

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
        self.loaded_packages = [Package.construct_from_dict(self.conf, p) for p in cache]

    def generate_digraph(self, target_package):
        header = '"%s"[label=<<font face="DejaVuSans" point-size="14">'\
                 '<table border="0" cellborder="0" cellspacing="0">\n'
        title = '<tr><td><font point-size="20"><b>%s</b></font></td></tr>\n'
        specialization = '<tr><td><font color="blue">%s=%s</font></td></tr>\n'
        specialization_msg = '<tr><td><font color="blue">%s</font></td></tr>\n'
        dependency = '<tr><td><font color="orange">%s=%s</font></td></tr>\n'
        footer = '</table></font>>];\n'

        _, packages = self.find_all_dependencies(target_package)
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
                        f.write(f'"{_package.get_name()}"\n')

                write_package(package)
                f.write('}')
