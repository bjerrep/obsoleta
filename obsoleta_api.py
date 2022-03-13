import os
from obsoletacore import Obsoleta, UpDownstreamFilter
from package import Package
from common import Error, ErrorOk, Args
from errorcodes import ErrorCode


class ObsoletaApi:
    def __init__(self, conf, args=Args()):
        self.conf = conf
        self.args = args
        self.obsoleta = Obsoleta(self.conf, self.args)

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
        return Package.construct_from_package_path(self.conf, path)

    def find_all_packages(self, package_or_compact):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, packages = self.obsoleta.find_all_packages(package_or_compact)
        return error, packages

    def find_first_package(self, package_or_compact, strict=False):
        """
        Return tupple (error or ErrorOk, package found)
        If strict=True it is an error if more than one candidate package was found.

        For the case where strict=False and there are more than a single candidate
        package found then note that the name find_first_package is slightly misleading.
        The package returned will be the package with the highest version, not simply
        just the first found.
        """
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, package = self.obsoleta.find_first_package(package_or_compact, strict)
        return error, package

    def check(self, package_or_compact):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, errors = self.obsoleta.get_errors(package_or_compact)
        if error.has_error():
            return error, errors
        return error, f'check pass for {package_or_compact}'

    def tree(self, package_or_compact):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        errors, ret = self.obsoleta.dump_tree(package_or_compact)
        return errors, ret

    def buildorder(self, package_or_compact, printpaths=False):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, unresolved, resolved = self.obsoleta.dump_build_order(package_or_compact)
        if error.has_error():
            return error, None
        if unresolved:
            return Error(ErrorCode.RESOLVE_ERROR,
                         package_or_compact,
                         f'unable to fully resolve {package_or_compact}'), None
        if printpaths:
            result = [_package.get_path() for _package in resolved]
        else:
            result = resolved
        return ErrorOk(), result

    def list_missing(self, package_or_compact):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, err_list = self.obsoleta.get_errors(package_or_compact)
        ret = []
        for err in err_list:
            if err.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
                ret.append(err)
        if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
            ret.append(error)
        return error, ret

    def upstreams(self, package_or_compact, updown_stream_filter=UpDownstreamFilter.FollowTree, as_path_list=False):
        """ Find all/any upstream packages and return them as a list. (Upstream: packages that this
            package depends on as given by the depends section).
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'filter' of type UpDownstreamFilter
            Param: 'as_path_list', returns the paths rather than the package object list.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, result = self.obsoleta.locate_upstreams(package_or_compact,
                                                       filter=updown_stream_filter)
        if error.has_error():
            return error, f'unable to locate {package_or_compact}'
        if as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def downstreams(self, package_or_compact, updown_stream_filter=UpDownstreamFilter.FollowTree, as_path_list=False):
        """ Find all/any downstream packages and return them as a list.
            (Downstream: packages depending on the package specified)
            Param: 'package_or_compact' is a Package object or a string with compact name.
            Param: 'downstream_filter', see UpDownstreamFilter enum.
            Param: 'as_path_list' if default false return Package objects else path strings.
            Returns: tuple(errorcode, [Packages] or [paths] according to 'as_path_list' argument)
        """
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        error, result = self.obsoleta.locate_downstreams(package_or_compact,
                                                         filter=updown_stream_filter)
        if result and as_path_list:
            return error, "\n".join(p.get_path() for p in result)
        return error, result

    def generate_digraph(self, package_or_compact):
        package_or_compact = Package.auto_package(self.conf, package_or_compact)
        self.obsoleta.generate_digraph(package_or_compact)

    from obsoleta_bump import bump_impl

    def bump(self, package_or_compact, new_version, bump=False, dryrun=False, indent_messages=False):
        """ Replace the version in any downstream package(s) where package is found
            in the dependency list and also the version for the package itself.

            Param: 'package_or_compact'. Package to bump.
            Param: 'new_version'. Version as a string.
            Param: 'bump'. If True its a full recursive bump, if false its what is also
                    called 'bumpdirect' which only bumps explicit references.
            Param: 'dryrun'. Dont actually modify any files, just write what would have been done.
            Returns: tuple(errorcode, [informational text messages])

            The implementation is found in obsoleta_bump.py.
        """

        return self.bump_impl(package_or_compact,
                              new_version,
                              bump=bump,
                              dryrun=dryrun,
                              indent_messages=indent_messages)
