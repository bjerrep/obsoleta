from log import logger, deb, inf
from version import Version
from package import anyarch, Track, TrackToString, track_from_string, buildtype_unknown
from common import get_local_time_tz, Args
from exceptions import BadPackageFile
from enum import Enum
import json, os, logging


class TrackSetScope(Enum):
    DOWNSTREAM = 0
    UPGRADE = 1
    FORCE = 2


class Dixi:
    def __init__(self, package, args=Args()):
        self.package = package
        self.dict = self.package.to_dict()
        self.action = package.to_string() + ' - '
        self.new_track = False
        if args.verbose:
            logger.setLevel(logging.DEBUG)

    def get_target(self):
        return self.package.get_name()

    def to_merged_json(self):
        if self.package.slot_unresolved:
            return 'need the key for slot/multislot package merge'

        return json.dumps(self.package.to_dict(), indent=2)

    def get_package(self, depend_package=None):
        if depend_package:
            return self.package.find_dependency(depend_package)
        return self.package

    def get_compact(self, delimiter):
        return self.package.to_compact_string(delimiter)

    def get_original_dict(self, depends_package=None):
        try:
            dependency = self.package.find_dependency(depends_package)
            return dependency.get_original_dict()
        except:
            if not self.package.get_original_dict():
                raise BadPackageFile('package not from model, %s' % self.package)
            return self.package.get_original_dict()

    def add_action(self, action):
        self.action += action
        inf(self.action)

    def getter(self, key, package=None):
        """
        A getter just a little too magic for comfort. If a depends package is given
        then the key is looked up for this. If not then the key is looked up in
        the key section for a slot/multislot package and finally the key is searched
        in the package itself.
        """
        unmodified_dict = self.get_original_dict(package)

        if package:
            try:
                return '', unmodified_dict[key]
            except:
                pass

        try:
            slot_key = self.package.get_slot_key()
            if slot_key:
                deb('getter looking in %s' % str(slot_key))
                return slot_key, unmodified_dict[slot_key][key]
        except:
            pass

        package_key = self.package.get_package_key()
        try:
            deb('getter looking in %s' % str(package_key))
            if package_key:
                return package_key, unmodified_dict[package_key][key]
            else:
                return '', unmodified_dict[key]
        except:
            pass
        return package_key, None

    def setter(self, section, key, value, package=None):
        unmodified_dict = self.get_original_dict(package)
        if not section or package:
            unmodified_dict[key] = value
        else:
            unmodified_dict[section][key] = value

    def set_version(self, version, depends_package=None):
        section, ver = self.getter('version', depends_package)
        org_version = str(Version(ver))
        self.setter(section, 'version', str(version), depends_package)
        action = 'version for %s rewritten from %s to %s' % (self.get_target(), org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        return org_version, str(version)

    def version_digit_increment(self, position):
        section, ver = self.getter('version')
        version = Version(ver)
        org_version = str(version)
        version.increase(position)
        self.setter(section, 'version', str(version))
        action = 'version for %s increased from %s to %s' % (self.get_target(), org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        return org_version, str(version)

    def version_digit_set(self, position, value):
        section, ver = self.getter('version')
        version = Version(ver)
        org_version = str(version)
        version.set(position, value)
        self.setter(section, 'version', str(version))
        action = 'version for %s changed from %s to %s' % (self.get_target(), org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        return org_version, str(version)

    def save(self, add_description=True):
        package_file = os.path.join(self.package.package_path, 'obsoleta.json')

        with open(package_file, 'w') as f:
            unmodified_dict = self.package.get_original_dict()
            if add_description:
                unmodified_dict['dixi_modified'] = get_local_time_tz()
                unmodified_dict['dixi_action'] = self.action
            f.write(json.dumps(unmodified_dict, indent=2))

    def set_track(self, track, track_scope):
        try:
            section, org_track = self.getter('track')
        except KeyError:
            org_track = Track.anytrack.value
        self.setter(section, 'track', track)
        action = 'track for %s changed from %s to %s' % (self.get_target(), org_track, track)
        if section:
            action += ' (section: %s)' % section

        if track_scope != TrackSetScope.DOWNSTREAM:
            track_Track = track_from_string(track)
            extra = ''
            for dependency in self.package.get_dependencies():
                if ((track_scope == TrackSetScope.UPGRADE and
                         track_Track > dependency.get_track()) or
                        (track_scope == TrackSetScope.FORCE)):
                    org_track = self.get_track(dependency)
                    self.setter(section, 'track', track, dependency)
                    extra += '%s from %s; ' % (dependency.get_name(), org_track)
            if extra:
                action += '. Changed [%s]' % extra

        self.add_action(action)
        return track

    def get_track(self, package=None):
        try:
            _, track = self.getter('track', package)
            if not track:
                return Track.anytrack.name
            return track
        except KeyError:
            return TrackToString[Track.anytrack.value]

    def set_arch(self, arch):
        section, org_arch = self.getter('arch')
        self.setter(section, 'arch', arch)
        action = 'arch for %s changed from %s to %s' % (self.get_target(), org_arch, arch)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        return arch

    def get_arch(self):
        try:
            _, arch = self.getter('arch')
            if not arch:
                return anyarch
            return arch
        except KeyError:
            return anyarch

    def set_buildtype(self, buildtype):
        section, org_buildtype = self.getter('buildtype')
        self.setter(section, 'buildtype', buildtype)
        action = 'buildtype for %s changed from %s to %s' % (self.get_target(), org_buildtype, buildtype)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        return buildtype

    def get_buildtype(self):
        try:
            _, buildtype = self.getter('buildtype')
            if not buildtype:
                return buildtype_unknown
            return buildtype
        except KeyError:
            return buildtype_unknown

    def get_value(self, key, depends_package=None):
        return self.getter(key, depends_package)[1]

    def set_value(self, key, value, depends_package=None):
        return self.setter(None, key, value, depends_package)
