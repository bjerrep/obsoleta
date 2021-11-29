from obsoletacore import Obsoleta, UpDownstreamFilter
from package import Package, anyarch
from common import Error, ErrorOk, Args
from errorcodes import ErrorCode
from dixi_api import DixiApi
from log import deb, inf
from version import Version
from exceptions import UnknownException
import os, copy


class ObsoletaApi:
    def __init__(self, setup, args=Args()):
        self.setup = setup
        self.args = args
        self.obsoleta = Obsoleta(self.setup, self.args)

    def clear_cache(self):
        os.remove(Obsoleta.default_cache_filename())

    def serialize(self):
        return self.obsoleta.serialize()

    def get_errors(self, package):
        return self.obsoleta.get_errors(package)

    def get_common_path(self):
        """ Get the common path for all roots. That was the idea anyway, for now return the root path if there is only
            one or else just give up.
        """
        if len(self.obsoleta.roots) > 1:
            return ''
        return self.obsoleta.roots[0]

    def make_package_from_path(self, path):
        return Package.construct_from_package_path(self.setup, path)

    def find_all_packages(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, packages = self.obsoleta.find_all_packages(package_or_compact)
        return error, packages

    def find_first_package(self, package_or_compact, strict=False):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, package = self.obsoleta.find_first_package(package_or_compact, strict)
        return error, package

    def check(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, errors = self.obsoleta.get_errors(package_or_compact)
        if error.has_error():
            return error, errors
        return error, 'check pass for %s' % package_or_compact

    def tree(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error = self.obsoleta.dump_tree(package_or_compact)
        return error

    def buildorder(self, package_or_compact, printpaths=False):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, unresolved, resolved = self.obsoleta.dump_build_order(package_or_compact)
        if error.has_error():
            return error, None
        if unresolved:
            return Error(ErrorCode.RESOLVE_ERROR,
                         package_or_compact,
                         'unable to fully resolve %s' % package_or_compact), None
        if printpaths:
            result = [_package.get_path() for _package in resolved]
        else:
            result = resolved
        return ErrorOk(), result

    def list_missing(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, err_list = self.obsoleta.get_errors(package_or_compact)
        ret = []
        for err in err_list:
            if err.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
                ret.append(err)
        if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
            ret.append(error)
        return error, ret

    def upstreams(self, package_or_compact, filter=UpDownstreamFilter.FollowTree, as_path_list=False):
        """ Find all/any upstream packages and return them as a list. (Upstream: packages that this
            package depends on as given by the depends section).
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'filter' of type UpDownstreamFilter
            Param: 'as_path_list', returns the paths rather than the package object list.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, result = self.obsoleta.locate_upstreams(package_or_compact,
                                                       filter=filter)
        if error.has_error():
            return error, 'unable to locate %s' % package_or_compact
        if as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def downstreams(self, package_or_compact, filter=UpDownstreamFilter.FollowTree, as_path_list=False):
        """ Find all/any downstream packages and return them as a list.
            (Downstream: packages depending on the package specified)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'downstream_filter', see UpDownstreamFilter enum.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, result = self.obsoleta.locate_downstreams(package_or_compact,
                                                         filter=filter)
        if error.has_error():
            return error, 'unable to locate downstreams for %s' % package_or_compact
        if as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def generate_digraph(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        self.obsoleta.generate_digraph(package_or_compact)

    def bump(self, package_or_compact, new_version, bump=False, dryrun=False):
        """ Replace the version in any downstream package(s) where package is found
            in the dependency list and also the version for the package itself.

            Param: 'package_or_compact'. Package to bump.
            Param: 'new_version'. Version as a string.
            Param: 'bump'. If True its a full recursive bump, if false its what is also
                    called 'bumpdirect' which only bumps explicit references.
            Param: 'dryrun'. Dont actually modify any files, just write what would have been done.
            Returns: tuple(errorcode, [informational text messages])
        """

        def bump_package(package_or_compact, new_version):
            ret = []
            package = Package.auto_package(self.setup, package_or_compact)
            dixi_api.load(package)
            old_version = dixi_api.set_version(new_version)[0]
            package_path = os.path.relpath(dixi_api.get_package().get_path(), self.get_common_path())

            if old_version == str(new_version):
                message = 'not bumping package "%s" (%s) already at version %s in "%s"' % (
                    dixi_api.get_package().get_name(),
                    dixi_api.get_package().to_string(),
                    old_version,
                    package_path)
            else:
                message = 'bumping package "%s" (%s) from %s to %s in "%s"' % (
                    dixi_api.get_package().get_name(),
                    dixi_api.get_package().to_string(),
                    old_version,
                    new_version,
                    package_path)

            ret.append(message)
            deb(message)
            if not dryrun:
                dixi_api.save()

            return ErrorOk(), ret

        def bump_downstreams(package, new_version, dependency_digit):
            inf('----- bump processing %s -----' % package)
            ret = []
            dixi_api.load(package)

            error, downstreams = self.downstreams(package, UpDownstreamFilter.ExplicitReferences)

            if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
                return ErrorOk(), ''
            elif error.has_error():
                return error, ['downstream search failed for {%s}' % package, ]

            inf('found %i "%s" downstream packages: "%s"' % (len(downstreams), package, downstreams))

            for downstream_package in downstreams:
                inf('bumping downstream package "%s" depends in parent "%s"' % (downstream_package, package))

                dixi_api.load(downstream_package.get_path(), downstream_package.slot_key)

                path = downstream_package.get_path()
                package_path = os.path.relpath(path, self.get_common_path())

                try:
                    skip_ranged = (self.args.skip_bumping_ranged_versions and
                                   not Version(downstream_package.get_package_value('version', package)).unique())
                except:
                    skip_ranged = False

                try:
                    skip_bump = downstream_package.get_package_value('bump', package) is False
                except:
                    skip_bump = False

                if skip_ranged or skip_bump:
                    downstream_version = dixi_api.get_version(downstream_package)

                    message = ('skipped downstream "%s" (%s) from %s to %s in "%s". skipbump=%s, skipranged=%s' % (
                        downstream_package.to_string(),
                        package.to_string(),
                        downstream_version,
                        new_version,
                        package_path,
                        skip_bump,
                        skip_ranged))
                    deb(message)
                    ret.append(message)
                    continue

                downstream_version = dixi_api.set_version(new_version, package)[0]

                extra = ''
                if downstream_package.get_slot_key():
                    extra += ' (slot "%s")' % downstream_package.get_slot_key()

                message = ('bumping dependency %s in downstream "%s" from %s to %s in "%s"%s' % (
                    package.to_string(),
                    downstream_package.get_name(),
                    downstream_version,
                    new_version,
                    package_path,
                    extra))

                deb(message)
                ret.append(message)

                if bump:
                    package_version = copy.deepcopy(downstream_package.get_version())

                    package_version.increase(dependency_digit)

                    message = 'bumping package "%s" (%s) from %s to %s in "%s"' % (
                        downstream_package.get_name(),
                        downstream_package.to_string(),
                        downstream_package.get_version(),
                        package_version,
                        package_path)

                    ret.append(message)
                    deb(message)

                    dixi_api.set_version(package_version)

                    if not dryrun:
                        dixi_api.save()

                    _error, _messages = bump_downstreams(downstream_package,
                                                         package_version,
                                                         dependency_digit=dependency_digit)
                    if _error.has_error():
                        raise UnknownException(_error)
                    ret.extend(_messages)
                else:
                    if not dryrun:
                        dixi_api.save()

            return ErrorOk(), ret

        if dryrun:
            inf(' - this is a dryrun, changes are not saved -')

        dixi_api = DixiApi(self.setup)

        relaxed = False

        target_package = Package.auto_package(self.setup, package_or_compact)

        err, current_package = self.obsoleta.find_first_package(target_package)
        current_version = current_package.get_version()
        dependency_digit = Version(current_version).get_change(new_version)

        if package_or_compact.get_arch() == anyarch:
            relaxed = True
            all_archs = self.obsoleta.get_all_archs()

            inf('bumping for the architectures %s' % str(all_archs))
            packages = []
            for arch in all_archs:
                if arch == 'anyarch':
                    continue
                _p = copy.copy(target_package)
                _p.set_arch(arch)
                packages.append(_p)
            # make the order deterministic to aid when testing
            packages = sorted(packages, key=Package.to_string)
        else:
            packages = [target_package]

        ret = []
        already_processed = []
        for package in packages:
            error, _package = self.obsoleta.find_first_package(package, strict=True)

            if _package in already_processed:
                continue

            already_processed.append(_package)

            if error.has_error():
                if relaxed:
                    inf('relaxed mode, ignoring not found %s' % package)
                    continue
                return error, 'failed to find unique package to process'

            error, messages = bump_package(copy.deepcopy(_package), new_version)
            ret += messages

            error, messages = bump_downstreams(_package, new_version, dependency_digit=dependency_digit)
            ret += messages

        return ErrorOk(), ret
