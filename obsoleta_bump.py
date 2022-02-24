from dixi_api import DixiApi
from package import Package, anyarch
from log import deb, inf, indent, unindent, get_indent
from common import ErrorOk
from version import Version
from exceptions import UnknownException, ObsoletaException, PackageNotFound
from obsoletacore import UpDownstreamFilter
from errorcodes import ErrorCode
import os, copy


def bump_impl(self, package_or_compact, new_version, bump=False, dryrun=False, indent_messages=False):
    """ imported as class method in obsoleta_api
    """

    def bump_package(package_or_compact, new_version):
        ret = []
        package = Package.auto_package(self.conf, package_or_compact)
        dixi_api.load(package)
        old_version = dixi_api.set_version(new_version)[0]
        package_path = os.path.relpath(dixi_api.get_package().get_path(), self.get_common_path())

        if old_version == str(new_version):
            message = 'not bumping package "%s" (%s) already at version %s in "%s"' % (
                dixi_api.get_package().get_name(),
                dixi_api.get_package().to_string(),
                old_version,
                package_path)
        else:
            message = 'bumping package "%s" (%s) from %s to %s in "%s"' % (
                dixi_api.get_package().get_name(),
                dixi_api.get_package().to_string(),
                old_version,
                new_version,
                package_path)

        ret.append(message)
        deb(message)
        if not dryrun:
            dixi_api.save()

        return ErrorOk(), ret

    def bump_downstreams(package, new_version, dependency_digit, ret=None):
        inf('----- bump processing %s -----' % package)
        if ret is None:
            ret = []
        dixi_api.load(package)

        error, downstreams = self.downstreams(package, UpDownstreamFilter.ExplicitReferences)

        if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
            return ErrorOk(), ''
        elif error.has_error():
            return error, ['downstream search failed for {%s}' % package, ]

        inf('"%s" has %i downstream packages:' % (package, len(downstreams)))
        for downstream in downstreams:
            inf('  %s' % downstream)

        if indent_messages:
            indent()

        for downstream_package in downstreams:
            inf('bumping downstream package "%s" depends in parent "%s"' % (downstream_package, package))

            dixi_api.load(downstream_package.get_path(), downstream_package.slot_key)

            path = downstream_package.get_path()
            package_path = os.path.relpath(path, self.get_common_path())

            skip_reason = ''
            try:
                if (self.args.skip_bumping_ranged_versions and
                        not Version(downstream_package.get_package_value('version', package)).unique()):
                    skip_reason += ' SKIPRANGED'
            except:
                pass

            try:
                if downstream_package.get_package_value('bump', package) is False:
                    skip_reason += ' BUMPFALSE'
            except:
                pass

            try:
                if downstream_package.get_readonly():
                    skip_reason += ' READONLY'
            except:
                pass

            if skip_reason:
                skip_reason = ' Reason:' + skip_reason
                downstream_version = dixi_api.get_version(downstream_package)

                message = ('skipped downstream "%s" (%s) from %s to %s in "%s".%s' % (
                    downstream_package.to_string(),
                    package.to_string(),
                    downstream_version,
                    new_version,
                    package_path,
                    skip_reason))

                message = get_indent() + message
                deb(message)
                ret.append(message)
                continue

            downstream_version = dixi_api.set_version(new_version, package)[0]

            extra = ''
            if downstream_package.get_slot_key():
                extra += ' (slot "%s")' % downstream_package.get_slot_key()

            message = ('bumping dependency %s in downstream "%s" from %s to %s in "%s"%s' % (
                package.to_string(),
                downstream_package.get_name(),
                downstream_version,
                new_version,
                package_path,
                extra))

            message = get_indent() + message
            deb(message)
            ret.append(message)

            if bump:
                package_version = copy.deepcopy(downstream_package.get_version())

                package_version.increase(dependency_digit)

                message = 'bumping package "%s" (%s) from %s to %s in "%s"' % (
                    downstream_package.get_name(),
                    downstream_package.to_string(),
                    downstream_package.get_version(),
                    package_version,
                    package_path)

                message = get_indent() + message
                ret.append(message)
                deb(message)

                dixi_api.set_version(package_version)

                if not dryrun:
                    dixi_api.save()

                _error, _ = bump_downstreams(downstream_package,
                                             package_version,
                                             dependency_digit=dependency_digit,
                                             ret=ret)
                if _error.has_error():
                    raise UnknownException(_error)

            else:
                if not dryrun:
                    dixi_api.save()

            if indent_messages:
                unindent()

        return ErrorOk(), ret

    if dryrun:
        inf(' - this is a dryrun, changes are not saved -')

    dixi_api = DixiApi(self.conf)

    relaxed = False

    target_package = Package.auto_package(self.conf, package_or_compact)

    err, current_package = self.obsoleta.find_first_package(target_package)
    current_version = current_package.get_version()
    dependency_digit = Version(current_version).get_change(new_version)
    if not dependency_digit:
        raise ObsoletaException('bump from %s to %s failed' % (current_version, new_version), ErrorCode.SYNTAX_ERROR)

    if package_or_compact.get_arch() == anyarch:
        relaxed = True
        all_archs = self.obsoleta.get_all_archs()

        inf('bumping for the architectures %s' % str(all_archs))
        packages = []
        for arch in all_archs:
            if arch == 'anyarch':
                continue
            _p = copy.copy(target_package)
            _p.set_arch(arch)
            packages.append(_p)
        # make the order deterministic to aid when testing
        packages = sorted(packages, key=Package.to_string)
    else:
        packages = [target_package]

    ret = []
    already_processed = []
    for package in packages:
        error, _package = self.obsoleta.find_first_package(package, strict=True)

        if not _package:
            raise PackageNotFound('dependency %s not found' % package)

        if _package in already_processed:
            continue

        already_processed.append(_package)

        if error.has_error():
            if relaxed:
                inf('relaxed mode, ignoring not found %s' % package)
                continue
            return error, 'failed to find unique package to process'

        error, messages = bump_package(copy.deepcopy(_package), new_version)
        ret += messages

        error, messages = bump_downstreams(_package, new_version, dependency_digit=dependency_digit)
        ret += messages

    return ErrorOk(), ret
