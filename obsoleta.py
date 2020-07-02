#!/usr/bin/env python3
from log import logger
from log import inf, deb, err, print_result, print_result_nl
from common import Setup
from errorcodes import ErrorCode
from package import Package
from obsoletacore import Obsoleta
from obsoleta_api import ObsoletaApi
from exceptions import ObsoletaException
import argparse, json, logging, os, traceback

# This is the script for calling obsoleta from the command line.

parser = argparse.ArgumentParser('obsoleta')
parser.add_argument('--package',
                    help='the package in compact form or "all". See also --path')
parser.add_argument('--path',
                    help='the path for the package. See also --package')
parser.add_argument('--root',
                    help='search root(s), ":" separated. '
                         'Use this and/or roots in obsoleta.conf (default runs from current)')
parser.add_argument('--depth',
                    help='search depth relative to root(s). Default 1')
parser.add_argument('--blacklist_paths', action='store',
                    help=': separated list of blacklist substrings')
parser.add_argument('--keepgoing', action='store_true',
                    help='attempt to ignore e.g. packages with otherwise fatal errors')

parser.add_argument('--check', action='store_true',
                    help='command: check a specified package')
parser.add_argument('--tree', action='store_true',
                    help='command: show tree for a package')
parser.add_argument('--buildorder', action='store_true',
                    help='command: show dependencies in building order for a package')
parser.add_argument('--upstream', action='store_true',
                    help='command: get the paths for the packages matching --package. Notice that the "last package '
                         'for an end-artifact" will itself be an upsteam package which can be slightly confusing')
parser.add_argument('--downstream', action='store_true',
                    help='command: get the paths for packages using the package given with --package')
parser.add_argument('--digraph', action='store_true',
                    help='command: make dependency plot for the package given with --package')

parser.add_argument('--bump', action='store_true',
                    help='command: bump the version for --package, both downstream and upstream. Requires --version')
parser.add_argument('--version',
                    help='the new version x.y.z, used with --bump')

parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')

parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--clearcache', action='store_true',
                    help='delete the cache file')
parser.add_argument('--dumpcache', action='store_true',
                    help='generate a cache file and dump on stdout (for analysis)')
parser.add_argument('--verbose', action='store_true',
                    help='enable all log messages (and stacktraces on unhandled exceptions)')
parser.add_argument('--info', action='store_true',
                    help='enable informational log messages')
parser.add_argument('--yappi', action='store_true',
                    help='run yappi profiler')


args = parser.parse_args()

if args.yappi:
    import yappirun
    yappirun.start_yappi()

if args.verbose:
    logger.setLevel(logging.DEBUG)
elif args.info:
    logger.setLevel(logging.INFO)

valid_package_action = args.tree or args.check or args.buildorder or args.upstream or \
                       args.downstream or args.bump or args.digraph

valid_command = valid_package_action or args.dumpcache

if args.clearcache:
    # clearcache can be used as standalone command
    try:
        os.remove(Obsoleta.default_cache_filename())
        inf('cache cleared (%s)' % Obsoleta.default_cache_filename())
    except:
        err('cache not found')
    if not valid_command:
        # clearcache was a standalone invocation, we're good
        exit(0)

# go-no-go checks

if not valid_command:
    err('no action specified (use --check, --tree, --buildorder, --upstream, --downstream or --dumpcache')
    exit(ErrorCode.MISSING_INPUT.value)

if not args.dumpcache and not args.package and not args.path:
    err('no package specified (use --package for compact form or --path for package dir)')
    exit(ErrorCode.MISSING_INPUT.value)

# parse configuration file

setup = Setup(args.conffile)

if args.depth:
    # a depth given on the commandline overrules any depth there might have been in the configuration file
    setup.depth = int(args.depth)
if args.keepgoing:
    setup.keepgoing = True

setup.dump()
exit_code = ErrorCode.OK

# construct obsoleta, load and parse everything in one go

try:
    obsoleta = ObsoletaApi(setup, args)

    if args.dumpcache:
        print_result_nl(json.dumps(obsoleta.serialize(), indent=4))
        if not valid_package_action:
            exit(ErrorCode.OK.value)

    if args.path:
        try:
            package = Package.construct_from_package_path(setup, args.path)
        except FileNotFoundError as e:
            err(str(e))
            exit(ErrorCode.PACKAGE_NOT_FOUND.value)
    else:
        package = Package.construct_from_compact(setup, args.package)

except ObsoletaException as e:
    err(str(e))
    exit_code = e.ErrorCode
except Exception as e:
    err('caught unexpected exception: %s' % str(e))
    if args.verbose:
        print(traceback.format_exc())
    exit(ErrorCode.UNKNOWN_EXCEPTION.value)

# and now figure out what to do

if exit_code != ErrorCode.OK:
    pass

elif args.check:
    deb('checking package "%s"' % package)
    error, errors = obsoleta.get_errors(package)

    if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
        err(error.get_message())
        exit_code = error.get_errorcode()
    elif error.has_error():
        err('checking package "%s": failed, %i errors found' % (package, len(errors)))
        for error in errors:
            err('   ' + error.to_string())
            exit_code = error.get_errorcode()
    else:
        inf('checking package "%s": success' % package)
        exit_code = ErrorCode.OK

elif args.tree:
    inf('package tree for "%s"' % package)
    error, result = obsoleta.tree(package)
    if error.is_ok():
        print_result("\n".join(result))
    else:
        err(error.print())
    exit_code = error.get_errorcode()

elif args.buildorder:
    exit_code = ErrorCode.OK
    deb('packages listed in buildorder')
    error, resolved = obsoleta.buildorder(package)

    if error.get_errorcode() == ErrorCode.RESOLVE_ERROR:
        err(error.get_message())
        exit_code = error.get_errorcode()
    elif error.has_error():
        err(' - unable to find somewhere to start, %s not found (circular dependency)' % package.to_string())
        exit(ErrorCode.CIRCULAR_DEPENDENCY.value)
    else:
        for _package in resolved:
            if args.printpaths:
                print_result(_package.get_path(), True)
            else:
                print_result(_package.to_string(), True)

            errors = _package.get_root_error()
            if errors:
                for error in errors:
                    exit_code = error.get_errorcode()
                    err(' - error: ' + error.to_string())

elif args.upstream:
    error, lookup = obsoleta.upstreams(package)
    if error.is_ok():
        print_result("\n".join(p.get_path() for p in lookup))
        exit_code = ErrorCode.OK
    else:
        err('unable to locate upstream %s' % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.downstream:
    error, lookup = obsoleta.downstreams(package)
    if error.is_ok():
        print_result("\n".join(p.get_path() for p in lookup))
        exit_code = ErrorCode.OK
    else:
        err('unable to locate downstream %s' % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.dumpcache:
    pass

elif args.bump:
    if not args.version:
        exit_code = ErrorCode.MISSING_INPUT
    else:
        error, messages = obsoleta.bump(package, args.version)
        if error.is_ok():
            print_result_nl("\n".join(line for line in messages))
            exit_code = ErrorCode.OK
        else:
            err('unable to locate %s' % package)
            exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.digraph:
    obsoleta.generate_digraph(package, '%s.gv' % package.get_name())

else:
    err("no valid command found")

if exit_code != ErrorCode.OK:
    print()
    err('failed with error %i: %s' % (exit_code.value, ErrorCode.to_string(exit_code.value)))

if args.yappi:
    yappirun.stop_yappi()

exit(exit_code.value)
