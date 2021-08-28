from obsoletacore import Obsoleta, DownstreamFilter
from package import Package
from common import Error, ErrorOk, Args
from errorcodes import ErrorCode
from dixi_api import DixiApi
from log import deb, inf, war
from version import Version
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
        return error, ret

    def upstreams(self, package_or_compact, as_path_list=False, full_tree=False):
        """ Find all/any upstream packages and return them as a list. (Upstream: packages matching the name)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, result = self.obsoleta.locate_upstreams(package_or_compact, full_tree)
        if error.has_error():
            return error, 'unable to locate %s' % package_or_compact
        if as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def downstreams(self, package_or_compact, downstream_filter, as_path_list=False):
        """ Find all/any downstream packages and return them as a list.
            (Downstream: packages depending on the package specified)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Param: 'find_all' default False where only explicit downstreams are returned, i.e where
                    the target package is listed directly in a downstream package depends list.
                    Set to True to get the full dependency list
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, result = self.obsoleta.locate_downstreams(package_or_compact,
                                                         downstream_filter=downstream_filter)
        if error.has_error():
            return error, 'unable to locate downstreams for %s' % package_or_compact
        if as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def generate_digraph(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        self.obsoleta.generate_digraph(package_or_compact)

    def bump(self, package_or_compact, new_version, dryrun=False):
        """ Replace the version in any downstream package(s) where package is found
            in the dependency list and also the version for the package itself.

            Param: 'package_or_compact'. Package to bump. It may contain "all" as arch (name:::all)
                    in which case the package will be bumped for all arch it is found in.
            Param: 'new_version'. Version as a string.
            Param: 'dryrun'. Dont actually modify any files, just write what would have been done.
            Returns: tuple(errorcode, [informational text messages])
        """
        def bump_package(package_or_compact, new_version, dryrun):
            ret = []
            package = Package.auto_package(self.setup, package_or_compact)
            dixi_api = DixiApi(self.setup)

            # the package given is the upstream package in this context, bump it as the first thing
            dixi_api.load(package)
            old_version = dixi_api.set_version(new_version)[0]
            package_path = os.path.relpath(dixi_api.get_package().get_path(), self.get_common_path())

            if old_version == str(new_version):
                message = 'not bumping upstream "%s" (%s) already at version %s in "%s"' % (
                    dixi_api.get_package().get_name(),
                    dixi_api.get_package().to_string(),
                    old_version,
                    package_path)
            else:
                message = 'bumped upstream "%s" (%s) from %s to %s in "%s"' % (
                    dixi_api.get_package().get_name(),
                    dixi_api.get_package().to_string(),
                    old_version,
                    new_version,
                    package_path)

            ret.append(message)
            deb(message)

            if not dryrun:
                dixi_api.save()

            # now bump all downstreams referencing the package in their depends section
            error, downstreams = self.downstreams(package, DownstreamFilter.ExplicitReferences)

            if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
                ret.append('no {%s} downstream packages found' % package.to_string())
            elif error.has_error():
                return error, ['downstream search failed for {%s}' % package, ]
            else:
                for downstream_package in downstreams:
                    # Make the version bump. Notice that the downstream package is reloaded
                    # since the Obsoleta packages are by now too digested to be of use here.
                    dixi_api.load(downstream_package.get_path(), downstream_package.slot_key)

                    old_version = dixi_api.get_version(package)
                    skip_ranged = self.args.skip_bumping_ranged_versions and not Version(old_version).unique()
                    try:
                        skip_bump = dixi_api.dixi.get_original_dict(package)['bump'] is False
                    except:
                        skip_bump = False
                    if skip_ranged or skip_bump:
                        message = ('skipped downstream "%s" (%s) from %s to %s in "%s". bump=%s, skipranged=%s' % (
                            downstream_package.get_name(),
                            package.to_string(),
                            old_version,
                            new_version,
                            package_path,
                            skip_bump,
                            skip_ranged))
                        deb(message)
                        ret.append(message)
                        continue

                    package.set_version('*')
                    old_version = dixi_api.set_version(new_version, package)[0]
                    if old_version == str(new_version):
                        continue

                    # generate a message about what was done
                    path = downstream_package.get_path()
                    package_path = os.path.relpath(path, self.get_common_path())

                    message = ('bumped downstream "%s" (%s) from %s to %s in "%s"' % (
                                downstream_package.get_name(),
                                package.to_string(),
                                old_version,
                                new_version,
                                package_path))
                    deb(message)
                    ret.append(message)

                    if not dryrun:
                        dixi_api.save()

            return ErrorOk(), ret

        if dryrun:
            inf(' - this is a dryrun, changes are not saved -')

        relaxed = False

        if package_or_compact.get_arch() == 'all':
            relaxed = True
            all_archs = self.obsoleta.get_all_archs()
            inf('bumping for the architectures %s' % str(all_archs))
            packages = []
            for arch in all_archs:
                _p = copy.copy(package_or_compact)
                _p.set_arch(arch)
                packages.append(_p)
            packages = sorted(packages, key=Package.to_string)
        else:
            packages = [package_or_compact]

        ret = []
        for package in packages:
            error, _package = self.obsoleta.find_first_package(package, strict=True)
            if error.has_error():
                if relaxed:
                    war('relaxed mode, ignoring not found %s' % package)
                    continue
                return error, 'failed to find unique package to process'
            error, messages = bump_package(_package, new_version, dryrun)
            ret += messages
        return ErrorOk(), ret
