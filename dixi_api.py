from common import Setup, Param, get_package_filepath, get_key_filepath
from errorcodes import ErrorCode
from package import Package
import os


class DixiApi:
    def __init__(self, conf, param=Param()):
        self.setup = Setup(conf)
        self.args = param

    def make_package(self, path=None):
        if not path:
            path = self.setup.paths
        package_path = get_package_filepath(path)
        if Package.is_multislot(package_path):
            if not self.args.keypath:
                raise Exception('the key directory to use is required for a multislot package', ErrorCode.MULTISLOT_ERROR)
            key_file = os.path.join(path, get_key_filepath(self.args.keypath))
            return Package.construct_from_multislot_package_path(self.setup, path, key_file)
        else:
            return Package.construct_from_package_path(self.setup, path)

    def get_compact(self, path=None):
        try:
            return True, self.make_package(path).to_string()
        except Exception as e:
            return False, str(e)
