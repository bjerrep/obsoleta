from log import logger as log
from version import Version
from package import Layout
import json, os, datetime, time


class Dixi:
    def __init__(self, package, depends_package=None):
        self.package = package
        self.depends_package = depends_package
        self.dict = self.package.to_dict()
        self.action = package.to_string() + ' - '
        self.new_version = False
        self.new_track = False

    def dump(self):
        return json.dumps(self.dict, indent=2)

    def get_package(self):
        if self.depends_package:
            return self.package.get_dependency(self.depends_package)
        return self.package

    def get_unmodified_dict(self):
        try:
            return self.package.get_dependency(self.depends_package).to_unmodified_dict()
        except:
            return self.package.to_unmodified_dict()

    def add_action(self, action):
        self.action += action
        log.info(self.action)

    def getter(self, key):
        unmodified_dict = self.get_unmodified_dict()
        if self.package.layout == Layout.standard or self.depends_package:
            return '', unmodified_dict[key]

        try:
            return self.package.key, unmodified_dict[self.package.key][key]
        except:
            try:
                return 'slot', unmodified_dict['slot'][key]
            except:
                return 'multislot', unmodified_dict['multislot'][key]

    def setter(self, section, key, value):
        unmodified_dict = self.get_unmodified_dict()
        if not section:
            unmodified_dict[key] = value
        else:
            unmodified_dict[section][key] = value

    def set_version(self, version):
        section, ver = self.getter('version')
        org_version = str(Version(ver))
        self.setter(section, 'version', version)
        action = 'version increased from %s to %s' % (org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return str(version)

    def version_digit_increment(self, position):
        section, ver = self.getter('version')
        version = Version(ver)
        org_version = str(version)
        version.increase(position)
        self.setter(section, 'version', str(version))
        action = 'version increased from %s to %s' % (org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return str(version)

    def version_digit_set(self, position, value):
        section, ver = self.getter('version')
        version = Version(ver)
        org_version = str(version)
        version.set(position, value)
        self.setter(section, 'version', str(version))
        action = 'version changed from %s to %s' % (org_version, version)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return str(version)

    def save(self):
        package_file = os.path.join(self.package.package_path, 'obsoleta.json')

        with open(package_file, 'w') as f:
            utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
            utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
            now = datetime.datetime.now()
            local_with_tz = now.replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset)).isoformat()

            unmodified_dict = self.package.to_unmodified_dict()
            unmodified_dict['dixi_modified'] = local_with_tz
            unmodified_dict['dixi_action'] = self.action
            f.write(json.dumps(unmodified_dict, indent=2))

    def set_track(self, track):
        section, org_track = self.getter('track')
        self.setter(section, 'track', track)
        action = 'track from %s to %s' % (org_track, track)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return track

    def get_track(self):
        _, track = self.getter('track')
        return track

    def set_arch(self, arch):
        section, org_arch = self.getter('arch')
        self.setter(section, 'arch', arch)
        action = 'arch from %s to %s' % (org_arch, arch)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return arch

    def get_arch(self):
        _, arch = self.getter('arch')
        return arch

    def set_buildtype(self, buildtype):
        section, org_buildtype = self.getter('buildtype')
        self.setter(section, 'buildtype', buildtype)
        action = 'buildtype from %s to %s' % (org_buildtype, buildtype)
        if section:
            action += ' (section: %s)' % section
        self.add_action(action)
        self.new_version = True
        return buildtype

    def get_buildtype(self):
        _, buildtype = self.getter('buildtype')
        return buildtype
