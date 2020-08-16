from common import Param
from package import Package
from dixicore import Dixi


class DixiApi:
    """ Python api for dixi.
        Might in time just be merged into dixicore and then there will just be 'dixi'.
    """
    def __init__(self, setup, param=Param()):
        """ Notice that the constructor does not give a usable DixiApi since it isn't told what package
            to work with. It should always be followed by a call to load()
        """
        self.setup = setup
        self.args = param
        self.dixi = None

    def load(self, path_or_package, depends_package=None):
        if isinstance(path_or_package, Package):
            self.dixi = Dixi(path_or_package, depends_package)
        else:
            self.dixi = Dixi(Package.construct_from_package_path(self.setup, path_or_package), depends_package)

    def get_package(self):
        return self.dixi.get_package()

    def get_compact(self, delimiter=':'):
        return self.dixi.get_compact(delimiter)

    def set_version(self, version):
        return self.dixi.set_version(version)

    def get_version(self):
        slot, version = self.dixi.getter('version')
        return version

    def get_value(self, key):
        return self.dixi.get_value(key)

    def set_value(self, key, value):
        return self.dixi.set_value(key, value)

    def save(self):
        self.dixi.save()
