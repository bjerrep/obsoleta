from obsoletacore import Obsoleta, DownstreamFilter
from package import Package
from common import Error, ErrorOk, Param
from errorcodes import ErrorCode
from dixi_api import DixiApi
from log import deb
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

    def make_package_from_path(self, path):
        return Package.construct_from_package_path(self.setup, path)

    def find_package(self, package_or_compact):
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        return self.obsoleta.find_package(package_or_compact)

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
        return self.obsoleta.get_errors(package_or_compact)

    def upstreams(self, package_or_compact, as_path_list=False):
        """ Find all/any upstream packages and return them as a list. (Upstream: packages matching the name)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.setup, package_or_compact)
        error, result = self.obsoleta.locate_upstreams(package_or_compact)
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

    def bump(self, package_or_compact, new_version):
        """ Replace the version in any downstream package(s) where package is found
            in the dependency list and also the version for the package itself.

            Param: 'package'. Package from the loaded package files list
            Param: 'new_version', version as a string.
            Returns: tuple(errorcode, [informational text messages])
        """

        ret = []
        package = Package.auto_package(self.setup, package_or_compact)
        dixi_api = DixiApi(self.setup)

        # the package given is the upstream package in this context, bump it as the first thing
        dixi_api.load(package)
        old_version = dixi_api.set_version(new_version)[0]
        package_path = os.path.relpath(dixi_api.get_package().get_path(), self.get_common_path())
        ret.append('bumped upstream {%s} from %s to %s in "%s"' %
                   (dixi_api.get_package().to_string(),
                    old_version,
                    new_version,
                    package_path))
        dixi_api.save()

        # now bump all downstreams referencing the package in their depends section
        error, downstreams = self.downstreams(package, DownstreamFilter.ExplicitReferences)

        if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
            ret.append('no {%s} downstream packages found' % package.to_string())
        elif error.has_error():
            return error, ['downstream search failed for {%s}' % package, ]
        else:
            for downstream_package in downstreams:
                # Make the version bump. Notice that Dixi is forced to reload the
                # package since it gets a path rather than a package from Obsoleta.
                # The Obsoleta packages are too digested to be of use here.
                dixi_api.load(downstream_package.get_path())
                old_version = dixi_api.set_version(new_version, package)[0]

                # generate a message about what was done
                parent_path = dixi_api.get_package(package).get_parent().get_path()
                package_path = os.path.relpath(parent_path, self.get_common_path())

                message = ('bumped downstream {%s} from %s to %s in "%s"' %
                          (dixi_api.get_package(package).to_string(), old_version, new_version, package_path))
                ret.append(message)
                deb(message)
                dixi_api.save()

        return ErrorOk(), ret
