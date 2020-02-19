#!/usr/bin/env python3
from log import deb, inf, err, cri, print_result, logger
from common import ErrorCode, Setup, Exceptio
from common import get_package_filepath, get_key_filepath
from package import Package
from dixicore import Dixi
import json, os, logging, argparse

# ---------------------------------------------------------------------------------------------


parser = argparse.ArgumentParser('dixi', description='''
    dixi is used for inquiring and modifying a specific package file with the intention
    that it should rarely be necessary to edit a package file directly.
    ''')
parser.add_argument('--path',
                    help='the path for the package to work on')
parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')

parser.add_argument('--print', action='store_true',
                    help='command: pretty print the packagefile')
parser.add_argument('--printtemplate', action='store_true',
                    help='print a blank obsoleta.json')
parser.add_argument('--printkey', metavar='key:value',
                    help='print a obsoleta.key on stdout. Argument value is the (multi)slot name')

parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify the package file')
parser.add_argument('--verbose', action='store_true',
                    help='enable all log messages')
parser.add_argument('--info', action='store_true',
                    help='enable informational log messages')
parser.add_argument('--newline', action='store_true',
                    help='the getters default runs without trailing newlines, this one adds them back in')
parser.add_argument('--keypath',
                    help='the relative keypath (directory name) to use for a multislotted package')
parser.add_argument('--depends',
                    help='target is the package in the depends section with the name given with --depends')

parser.add_argument('--getname', action='store_true',
                    help='command: get name')
parser.add_argument('--getcompact', action='store_true',
                    help='command: get compact name')
parser.add_argument('--delimiter',
                    help='delimiter used for getcompact (default ":"')

parser.add_argument('--getversion', action='store_true',
                    help='command: get version')
parser.add_argument('--setversion',
                    help='command: set the version to SETVERSION')

parser.add_argument('--incmajor', action='store_true',
                    help='command: increase the major with one')
parser.add_argument('--incminor', action='store_true',
                    help='command: increase the minor with one')
parser.add_argument('--incbuild', action='store_true',
                    help='command: increase the buildnumber with one')

parser.add_argument('--settrack',
                    help='command: set track')
parser.add_argument('--gettrack', action='store_true',
                    help='command: get track')

parser.add_argument('--setarch',
                    help='command: set arch')
parser.add_argument('--getarch', action='store_true',
                    help='command: get arch')

parser.add_argument('--setbuildtype',
                    help='command: set buildtype (e.g. release, debug)')
parser.add_argument('--getbuildtype', action='store_true',
                    help='command: get buildtype (e.g. release, debug)')

args = parser.parse_args()

if args.printtemplate:
    setup = Setup()
    setup.using_arch = True
    setup.using_buildtype = True
    setup.using_track = True
    _package = Package.construct_from_compact(setup, 'a:0.0.0:development:archname:buildtype')
    _depends = Package.construct_from_compact(setup, 'b:0.0.0:development:archname:buildtype')
    _package.add_dependency(_depends)
    package_file = Dixi(_package)
    print(package_file.dump())
    exit(ErrorCode.OK.value)

if args.printkey:
    key, value = args.printkey.split(':')
    _json = {key: value}
    print(json.dumps(_json, indent=4))
    exit(ErrorCode.OK.value)

if args.verbose:
    logger.setLevel(logging.DEBUG)
elif args.info:
    logger.setLevel(logging.INFO)

if not args.path:
    deb('no path given, using current directory')
    args.path = '.'

setup = Setup(args.conffile)

try:
    package_path = get_package_filepath(args.path)
    if Package.is_multislot(package_path):
        if not args.keypath:
            cri('the key directory to use is required for a multislot package', ErrorCode.MULTISLOT_ERROR)
        key_file = os.path.join(args.path, get_key_filepath(args.keypath))
        package = Package.construct_from_multislot_package_path(setup, args.path, key_file)
    else:
        package = Package.construct_from_package_path(setup, args.path)

except Exceptio as e:
    err(str(e))
    exit(e.ErrorCode.value)
except Exception as e:
    err(str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)

try:
    if args.depends:
        depends_package = package.get_dependency(args.depends)
        pf = Dixi(package, depends_package)
    else:
        pf = Dixi(package)

except FileNotFoundError as e:
    err('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

save_pending = False
ret = None

if args.getname:
    ret = pf.get_package().get_name()

elif args.getcompact:
    ret = pf.get_package().to_string()
    if args.delimiter:
        ret = ret.replace(':', args.delimiter)

elif args.getversion:
    ret = pf.get_package().get_version()

elif args.setversion:
    ret = pf.set_version(args.setversion)
    save_pending = True

elif args.incmajor:
    ret = pf.version_digit_increment(0)
    save_pending = True

elif args.incminor:
    ret = pf.version_digit_increment(1)
    save_pending = True

elif args.incbuild:
    ret = pf.version_digit_increment(2)
    save_pending = True

elif args.settrack:
    if not setup.using_track:
        cri('track identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.set_track(args.settrack)
    save_pending = True

elif args.gettrack:
    if not setup.using_track:
        cri('track identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.get_track()

elif args.setarch:
    if not setup.using_arch:
        cri('arch identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.set_arch(args.setarch)
    save_pending = True

elif args.getarch:
    if not setup.using_arch:
        cri('arch identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.get_arch()

elif args.setbuildtype:
    if not setup.using_buildtype:
        cri('buildtype identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.set_buildtype(args.setbuildtype)
    save_pending = True

elif args.getbuildtype:
    if not setup.using_buildtype:
        cri('buildtype identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
    ret = pf.get_buildtype()

elif args.print:
    print_result(pf.dump())

else:
    err('no command found')
    exit(ErrorCode.MISSING_INPUT.value)

if ret:
    print_result(str(ret), args.newline)

if save_pending:
    if args.dryrun:
        inf('\ndry run, package file is not rewritten')
    else:
        pf.save()

exit(ErrorCode.OK.value)
