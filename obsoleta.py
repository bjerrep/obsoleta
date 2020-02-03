#!/usr/bin/env python3
import argparse, json
from log import logger
from log import inf, deb, err, print_result, print_result_nl
import logging, os, traceback
from common import Setup, Exceptio
from errorcodes import ErrorCode
from package import Package
from obsoletacore import Obsoleta


parser = argparse.ArgumentParser('obsoleta')
parser.add_argument('--package',
                    help='the package in compact form or "all". See also --path')
parser.add_argument('--path',
                    help='the path for the package. See also --package')
parser.add_argument('--root',
                    help='search root(s), ":" separated. Use this and/or roots in obsoleta.conf (default runs from current)')
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
parser.add_argument('--locate', action='store_true',
                    help='command: get the path for the package given with --package')
parser.add_argument('--upstream', action='store_true',
                    help='command: get the path for any upstream package(s) using the package given with --package')

parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')

parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf')
parser.add_argument('--clearcache', action='store_true',
                    help='delete the cache file')
parser.add_argument('--dumpcache', action='store_true',
                    help='generate a cache file and dump on stdout (for analysis)')
parser.add_argument('--verbose', action='store_true',
                    help='enable all log messages')
parser.add_argument('--info', action='store_true',
                    help='enable informational log messages')


args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)
elif args.info:
    logger.setLevel(logging.INFO)

valid_command = args.tree or args.check or args.buildorder or args.locate or args.upstream or args.dumpcache

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
    err('no action specified (use --check, --tree, --buildorder, --locate, --upstream or --dumpcache')
    exit(ErrorCode.MISSING_INPUT.value)

if not args.package and not args.path:
    err('no package specified (use --package for compact form or --path for package dir)')
    exit(ErrorCode.MISSING_INPUT.value)

# parse configuration file

setup = Setup(args.conffile)

if args.depth:
    # a depth given on the commandline overrules any depth there might have been in the configuration file
    setup.depth = int(args.depth)

if args.dumpcache:
    setup.cache = True

setup.dump()

# construct obsoleta, load and parse everything in one go

try:
    obsoleta = Obsoleta(setup, args)

    if args.dumpcache:
        print_result_nl(json.dumps(obsoleta.serialize(), indent=4))

    if args.path:
        try:
            package = Package.construct_from_package_path(setup, args.path)
        except FileNotFoundError as e:
            err(str(e))
            exit(ErrorCode.PACKAGE_NOT_FOUND.value)
    else:
        package = Package.construct_from_compact(setup, args.package)

except Exceptio as e:
    err(str(e))
    err(ErrorCode.to_string(e.ErrorCode.value))
    exit(e.ErrorCode.value)
except Exception as e:
    err('caught unexpected exception: %s' % str(e))
    if args.verbose:
        print(traceback.format_exc())
    exit(ErrorCode.UNKNOWN_EXCEPTION.value)

exit_code = ErrorCode.UNSET

# and now figure out what to do

if args.check:
    deb('checking package "%s"' % package)
    errors = obsoleta.get_errors(package)

    if errors == ErrorCode.PACKAGE_NOT_FOUND:
        err('package "%s" not found' % package)
        exit_code = errors
    elif errors:
        err('checking package "%s": failed, %i errors found' % (package, len(errors)))
        for error in errors:
            err('   ' + error.to_string())
            exit_code = error.get_error()
    else:
        inf('checking package "%s": success' % package)
        exit_code = ErrorCode.OK

elif args.tree:
    inf('package tree for "%s"' % package)
    dump, error = obsoleta.dump_tree(package)
    if dump:
        print_result("\n".join(dump))
        exit_code = error
    else:
        inf("package '%s'not found" % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.buildorder:
    exit_code = ErrorCode.OK
    deb('packages listed in buildorder')
    unresolved, resolved = obsoleta.dump_build_order(package)

    if not resolved:
        err(' - unable to find somewhere to start, %s not found (circular dependency)' % package.to_string())
        exit(ErrorCode.CIRCULAR_DEPENDENCY.value)

    for _package in resolved:
        if args.printpaths:
            package_path = _package.get_path()
            if package_path:
                print_result(package_path, True)
            else:
                print_result(_package.to_string(), True)
        else:
            print_result(_package.to_string(), True)

        errors = _package.get_root_error()
        if errors:
            for error in errors:
                exit_code = error.get_error()
                err(' - error: ' + error.to_string())

    if unresolved:
        err('unable to resolve build order for the following packages (circular dependencies ?)')
        exit_code = ErrorCode.CIRCULAR_DEPENDENCY
        for _package in unresolved:
            err(' - ' + _package.to_string())

elif args.locate:
    lookup = obsoleta.lookup(package, strict=True)
    if lookup:
        print_result("\n".join(p.get_path() for p in lookup))
        exit_code = ErrorCode.OK
    else:
        err('unable to locate %s' % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.upstream:
    lookup = obsoleta.locate_upstreams(package)
    if lookup:
        print_result("\n".join(p.get_path() for p in lookup))
        exit_code = ErrorCode.OK
    else:
        err('unable to locate %s' % package)
        exit_code = ErrorCode.PACKAGE_NOT_FOUND

elif args.dumpcache:
    pass

else:
    err("no valid command found")

exit(exit_code.value)
