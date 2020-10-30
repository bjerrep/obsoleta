from common import Args
from package import Package, Track
from dixicore import Dixi, TrackSetScope


class DixiApi:
    """ Python api for dixi.
        Might in time just be merged into dixicore and then there will just be 'dixi'.
    """
    def __init__(self, setup, args=Args()):
        """ Notice that the constructor does not give a usable DixiApi since it isn't told what package
            to work with. It should always be followed by a call to load()
        """
        self.setup = setup
        self.args = args
        self.dixi = None

    def load(self, path_or_package):
        if isinstance(path_or_package, Package):
            self.dixi = Dixi(path_or_package)
        else:
            self.dixi = Dixi(Package.construct_from_package_path(self.setup, path_or_package, self.args.keypath))

    def get_package(self, depend_package=None):
        return self.dixi.get_package(depend_package)

    def get_compact(self, delimiter=':'):
        return self.dixi.get_compact(delimiter)

    def set_version(self, version, depends_package=None):
        return self.dixi.set_version(version, depends_package)

    def get_version(self, depends_package=None):
        slot, version = self.dixi.getter('version', depends_package)
        return version

    def get_value(self, key):
        return self.dixi.get_value(key)

    def set_value(self, key, value):
        return self.dixi.set_value(key, value)

    def set_track(self, track, track_scope=TrackSetScope.UPGRADE):
        if isinstance(track, Track):
            track = track.name
        return self.dixi.set_track(track, track_scope)

    def get_track(self, package=None):
        package = Package.auto_package(self.setup, package)
        return self.dixi.get_track(package)

    def get_layout(self):
        return self.dixi.get_package().get_layout()

    def print(self):
        """
        Returns pretty printed json string but doesn't actually print anything
        """
        return self.dixi.to_merged_json()

    def save(self):
        self.dixi.save()
