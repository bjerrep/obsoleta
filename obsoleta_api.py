from obsoletacore import Obsoleta
from package import Package
from common import Param
from errorcodes import ErrorCode, is_ok
from dixi_api import DixiApi
import os


class ObsoletaApi:
    def __init__(self, setup, param=Param()):
        self.setup = setup
        self.args = param
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

    def make_package_from_compact(self, package_or_compact):
        """
        Returns a Package object from its compact name. As a convinience it will
        just return the Package if it is given a Package.
        """
        if isinstance(package_or_compact, Package):
            return package_or_compact
        return Package.construct_from_compact(self.setup, package_or_compact)

    def make_package_from_path(self, path):
        return Package.construct_from_package_path(self.setup, path)

    def check(self, package_or_compact):
        package_or_compact = self.make_package_from_compact(package_or_compact)
        errorcode, errors = self.obsoleta.get_errors(package_or_compact)
        if errorcode != ErrorCode.OK:
            return errorcode, errors
        return errorcode, 'check pass for %s' % package_or_compact

    def tree(self, package_or_compact):
        package_or_compact = self.make_package_from_compact(package_or_compact)
        errorcode, errors = self.obsoleta.dump_tree(package_or_compact)
        return errorcode, errors

    def buildorder(self, package_or_compact, printpaths=False):
        package_or_compact = self.make_package_from_compact(package_or_compact)
        unresolved, resolved = self.obsoleta.dump_build_order(package_or_compact)
        if not resolved:
            return ErrorCode.RESOLVE_ERROR, 'unable to resolve %s' % package_or_compact
        if unresolved:
            return ErrorCode.RESOLVE_ERROR, 'unable to fully resolve %s' % package_or_compact
        if printpaths:
            result = [_package.get_path() for _package in resolved]
        else:
            result = resolved
        return ErrorCode.OK, result

    def upstreams(self, package_or_compact, as_path_list=False):
        """ Find all/any upstream packages and return them as a list. (Upstream: packages matching the name)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = self.make_package_from_compact(package_or_compact)
        errorcode, result = self.obsoleta.lookup(package_or_compact)
        if errorcode != ErrorCode.OK:
            return errorcode, 'unable to locate %s' % package_or_compact
        if as_path_list:
            return errorcode, "\n".join(p.get_path() for p in result)
        return errorcode, result

    def downstreams(self, package_or_compact, as_path_list=False):
        """ Find all/any downstream packages and return them as a list. (Downstream: packages depending on the package)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = self.make_package_from_compact(package_or_compact)
        errorcode, result = self.obsoleta.locate_downstreams(package_or_compact)
        if not is_ok(errorcode):
            return errorcode, 'unable to locate upstreams for %s' % package_or_compact
        if as_path_list:
            return errorcode, "\n".join(p.get_path() for p in result)
        return errorcode, result

    def bump(self, package_or_compact, new_version):
        """ Replace the version in any downstream package(s) where 'package_or_compact' is found
            in the dependency list and also in any 'package_or_compact' upstream package(s).

            Param: 'package_or_compact' can be both a Package object or a string with a compact name.
            Param: 'new_version', version as a string.
            Returns: tuple(errorcode, [informational text messages])
        """
        ret = []
        package = self.make_package_from_compact(package_or_compact)
        dixi_api = DixiApi(self.setup)

        errorcode, upstreams = self.upstreams(package_or_compact, True)

        if not is_ok(errorcode):
            return errorcode, ['unable to locate any upstreams for {%s}' % package_or_compact, ]

        for path in upstreams.split():
            dixi_api.load(path)
            old_version = dixi_api.set_version(new_version)[0]
            package_path = os.path.relpath(dixi_api.get_package().get_path(), self.get_common_path())
            ret.append('bumped upstream {%s} from %s to %s in "%s"' %
                       (dixi_api.get_package().to_string(),
                        old_version,
                        new_version,
                        package_path))
            dixi_api.save()

        errorcode, downstreams = self.downstreams(package, True)

        if errorcode == ErrorCode.PACKAGE_NOT_FOUND:
            ret.append('no {%s} downstream packages found' % str(package_or_compact))
        elif not is_ok(errorcode):
            return errorcode, ['downstream search failed for {%s}' % package_or_compact, ]
        else:
            for path in downstreams.split():
                dixi_api.load(path, package_or_compact)
                old_version = dixi_api.set_version(new_version)[0]
                parent_path = dixi_api.get_package().get_parent().get_path()
                package_path = os.path.relpath(parent_path, self.get_common_path())
                ret.append('bumped downstream {%s} from %s to %s in "%s"' %
                           (dixi_api.get_package().to_string(),
                            old_version,
                            new_version,
                            package_path))
                dixi_api.save()

        return ErrorCode.OK, ret
