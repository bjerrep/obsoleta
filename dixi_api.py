from package import Package, Track
from dixicore import Dixi, TrackSetScope


class DixiApi:
    """ Python api for dixi.
        Might in time just be merged into dixicore and then there will just be 'dixi'.
    """
    def __init__(self, conf):
        """ Notice that the constructor does not give a usable DixiApi since it isn't told what package
            to work with. It should always be followed by a call to load()
        """
        self.conf = conf
        self.dixi = None

    def load(self, path_or_package, key=None, keypath=None):
        if isinstance(path_or_package, Package):
            self.dixi = Dixi(path_or_package)
        else:
            package = Package.construct_from_package_path(
                self.conf,
                path_or_package,
                key=key,
                keypath=keypath)
            self.dixi = Dixi(package)

    def get_package(self, depend_package=None):
        return self.dixi.get_package(depend_package)

    def get_compact(self, delimiter=':'):
        return self.dixi.get_compact(delimiter)

    def set_version(self, version, depends_package=None):
        return self.dixi.set_version(version, depends_package)

    def get_version(self, depends_package=None):
        slot, version = self.dixi.getter('version', depends_package)
        return version

    def set_readonly(self, value: bool = True):
        """
        The only allowed set operation after set_readonly(True) is
        set_readonly(False) to remove the read only state.
        """
        self.dixi.set_readonly(value)

    def get_readonly(self):
        self.dixi.getter('readonly')

    def get_value(self, key, depends_package=None):
        return self.dixi.get_value(key, depends_package)

    def set_value(self, key, value, depends_package=None):
        return self.dixi.set_value(key, value, depends_package)

    def set_track(self, track, track_scope=TrackSetScope.UPGRADE):
        if isinstance(track, Track):
            track = track.name
        return self.dixi.set_track(track, track_scope)

    def get_track(self, package=None):
        package = Package.auto_package(self.conf, package)
        return self.dixi.get_track(package)

    def get_layout(self):
        return self.dixi.get_package().get_layout()

    def to_merged_json(self):
        return self.dixi.to_merged_json()

    def save(self):
        self.dixi.save()
