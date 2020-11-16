#!/usr/bin/env python3
from log import deb, inf, err, cri, print_result, logger
from common import Setup
from common import Position
from package import Package
from dixicore import Dixi, TrackSetScope
from errorcodes import ErrorCode
from exceptions import ObsoletaException
import generator
import json, logging, argparse, os

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

parser.add_argument('--generate_c', action='store_true',
                    help='generate c code for runtime obsoleta usage')
parser.add_argument('--generate_src', default='.',
                    help='source directory relative to package file. Defaults to package dir')
parser.add_argument('--generate_inc', default='.',
                    help='include directory relative to package file. Defaults to package dir')

parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify the package file')
parser.add_argument('--verbose', action='store_true',
                    help='enable all log messages')
parser.add_argument('--info', action='store_true',
                    help='enable informational log messages')
parser.add_argument('--newline', action='store_true',
                    help='the getters default runs without trailing newlines, this one adds them back in')
parser.add_argument('--keypath',
                    help='the relative keypath (directory name) to use for a multislotted package if a specific'
                         'slot needs to get resolved. See also --key.')
parser.add_argument('--key',
                    help='the key to use for a multislotted package if a specific slot needs to get resolved. '
                         'See also --keypath.')
parser.add_argument('--depends',
                    help='target is the package in the depends section with the name given with --depends')
parser.add_argument('--skiptags', action='store_true',
                    help='don\'t write a short description of last action into the package file. '
                         'It looks cool, but for slotted packages it might trigger merge conflicts.')

parser.add_argument('--getname', action='store_true',
                    help='command: get name')
parser.add_argument('--getcompact', action='store_true',
                    help='command: get compact name')
parser.add_argument('--delimiter', help='delimiter used for getcompact (default ":"')

parser.add_argument('--getversion', action='store_true',
                    help='command: get version')
parser.add_argument('--setversion', help='command: set the version to SETVERSION')

parser.add_argument('--incmajor', action='store_true',
                    help='command: increase the major with one')
parser.add_argument('--incminor', action='store_true',
                    help='command: increase the minor with one')
parser.add_argument('--incbuild', action='store_true',
                    help='command: increase the buildnumber with one')

parser.add_argument('--setmajor', help='command: set the major number')
parser.add_argument('--setminor', help='command: set the minor number')
parser.add_argument('--setbuild', help='command: set the build number')

parser.add_argument('--settrack', help='command: set track. See --settrackscope')
parser.add_argument('--settrackscope', default='upgrade',
                    help='set scope for settrack, downstream (only), upgrade (any too low) or force (all). '
                         'Default is upgrade')
parser.add_argument('--gettrack', action='store_true',
                    help='command: get track. Default returns "anytrack"')

parser.add_argument('--setarch', help='command: set arch')
parser.add_argument('--getarch', action='store_true',
                    help='command: get arch. Default returns "anyarch"')

parser.add_argument('--setbuildtype', help='command: set buildtype (e.g. release, debug)')
parser.add_argument('--getbuildtype', action='store_true',
                    help='command: get buildtype (e.g. release, debug). Default returns "unknown"')

parser.add_argument('--getvalue',
                    help='command: get the value for the given key')
parser.add_argument('--setvalue',
                    help='command: set the value for the given key. Use quotes as in '
                         '"key value becomes everything else"')


args = parser.parse_args()

if args.printtemplate:
    setup = Setup()
    setup.using_arch = True
    setup.using_buildtype = True
    setup.using_track = True
    _package = Package.construct_from_compact(setup, 'a:0.0.0:development:archname:buildtype')
    _depends = Package.construct_from_compact(setup, 'b:0.0.0:development:archname:buildtype')
    _package.add_dependency(_depends)
    dixi = Dixi(_package)
    print(dixi.to_merged_json())
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
    package = Package.construct_from_package_path(
        setup, args.path, key=args.key, keypath=args.keypath)
except ObsoletaException as e:
    err(str(e))
    exit(e.ErrorCode.value)
except Exception as e:
    err(str(e))
    exit(ErrorCode.SYNTAX_ERROR.value)

try:
    if args.depends:
        dependency = Package.construct_from_compact(setup, args.depends)
    else:
        dependency = None

    dx = Dixi(package)

except FileNotFoundError as e:
    err('caught exception: %s' % str(e))
    exit(ErrorCode.MISSING_INPUT.value)

save_pending = False
ret = None

try:
    if args.getname:
        ret = dx.get_package().get_name()

    elif args.getcompact:
        ret = dx.get_compact(args.delimiter)

    elif args.getversion:
        ret = dx.get_package(dependency).get_version()

    elif args.setversion:
        ret = dx.set_version(args.setversion, dependency)
        save_pending = True

    elif args.incmajor:
        ret = dx.version_digit_increment(Position.MAJOR)
        save_pending = True

    elif args.incminor:
        ret = dx.version_digit_increment(Position.MINOR)
        save_pending = True

    elif args.incbuild:
        ret = dx.version_digit_increment(Position.BUILD)
        save_pending = True

    elif args.setmajor:
        ret = dx.version_digit_set(Position.MAJOR, args.setmajor)
        save_pending = True

    elif args.setminor:
        ret = dx.version_digit_set(Position.MINOR, args.setminor)
        save_pending = True

    elif args.setbuild:
        ret = dx.version_digit_set(Position.BUILD, args.setbuild)
        save_pending = True

    elif args.settrack:
        if not setup.using_track:
            cri('track identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        scopes = ['downstream', 'upgrade', 'force']
        settrackscope = TrackSetScope(scopes.index(args.settrackscope))
        ret = dx.set_track(args.settrack, settrackscope)
        save_pending = True

    elif args.gettrack:
        if not setup.using_track:
            cri('track identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        ret = dx.get_track()

    elif args.setarch:
        if not setup.using_arch:
            cri('arch identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        ret = dx.set_arch(args.setarch)
        save_pending = True

    elif args.getarch:
        if not setup.using_arch:
            cri('arch identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        ret = dx.get_arch()

    elif args.setbuildtype:
        if not setup.using_buildtype:
            cri('buildtype identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        ret = dx.set_buildtype(args.setbuildtype)
        save_pending = True

    elif args.getbuildtype:
        if not setup.using_buildtype:
            cri('buildtype identifier is not enabled, see --conf', ErrorCode.OPTION_DISABLED)
        ret = dx.get_buildtype()

    elif args.getvalue:
        try:
            depends_package = Package.construct_from_compact(setup, args.depends)
        except:
            depends_package = None
        try:
            ret = dx.get_value(args.getvalue, depends_package)
        except:
            cri('key not found, "%s"' % args.getvalue, ErrorCode.SYNTAX_ERROR)

    elif args.setvalue:
        try:
            depends_package = Package.construct_from_compact(setup, args.depends)
        except:
            depends_package = None
        try:
            key, value = args.setvalue.split(maxsplit=1)
            ret = dx.set_value(key, value, depends_package)
            save_pending = True
        except Exception as e:
            cri('got ' + str(e), ErrorCode.SYNTAX_ERROR)

    elif args.print:
        print_result(dx.to_merged_json())

    elif args.generate_c:
        generator.generate_c(package,
                             os.path.join(package.get_path(), args.generate_src),
                             os.path.join(package.get_path(), args.generate_inc))
        save_pending = True

    else:
        err('no command found')
        exit(ErrorCode.MISSING_INPUT.value)

except Exception as e:
    err(str(e))
    exit(e.ErrorCode.value)

if ret:
    print_result(str(ret), args.newline)

if save_pending:
    if args.dryrun:
        inf('\ndry run, package file is not rewritten')
    else:
        dx.save(not args.skiptags)

exit(ErrorCode.OK.value)
