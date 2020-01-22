from obsoletacore import Obsoleta
from package import Package
from common import Setup, Param
from errorcodes import ErrorCode
import os


class ObsoletaApi:
    def __init__(self, conf, param=Param()):
        self.setup = Setup(conf)
        self.args = param
        self.obsoleta = Obsoleta(self.setup, self.args)

    def clear_cache(self):
        os.remove(Obsoleta.default_cache_filename())

    def make_package_from_compact(self, compact):
        return Package.construct_from_compact(self.setup, compact)

    def check(self, package_or_compact):
        if not isinstance(package_or_compact, Package):
            package_or_compact = self.make_package_from_compact(package_or_compact)
        error = self.obsoleta.get_errors(package_or_compact)
        if error:
            return False, error
        return True, 'check pass for %s' % package_or_compact

    def tree(self, package_or_compact):
        if not isinstance(package_or_compact, Package):
            package_or_compact = self.make_package_from_compact(package_or_compact)
        message, error = self.obsoleta.dump_tree(package_or_compact)
        if error != ErrorCode.OK:
            return False, message
        return True, message

    def buildorder(self, package_or_compact, printpaths=False):
        if not isinstance(package_or_compact, Package):
            package_or_compact = self.make_package_from_compact(package_or_compact)
        unresolved, resolved = self.obsoleta.dump_build_order(package_or_compact)
        if not resolved:
            return False, 'unable to resolve %s' % package_or_compact
        if unresolved:
            return False, 'unable to fully resolve %s' % package_or_compact
        if printpaths:
            result = [_package.get_path() for _package in resolved]
        else:
            result = [_package.to_string() for _package in resolved]
        return True, result

    def locate(self, package_or_compact):
        if not isinstance(package_or_compact, Package):
            package_or_compact = self.make_package_from_compact(package_or_compact)
        result = self.obsoleta.lookup(package_or_compact)
        if not result:
            return False, 'unable to locate %s' % package_or_compact
        return True, "\n".join(p.get_path() for p in result)

    def upstream(self, package_or_compact):
        if isinstance(package_or_compact, str):
            package_or_compact = self.make_package_from_compact(package_or_compact)
        result = self.obsoleta.locate_upstreams(package_or_compact, False)
        if not result:
            return False, 'unable to locate upstreams for %s' % package_or_compact
        return True, result
