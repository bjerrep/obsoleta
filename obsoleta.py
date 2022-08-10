#!/usr/bin/env python3
import argparse, json, os, traceback
from obsoleta.log import set_log_level, inf, deb, err, print_result, print_result_nl
from obsoleta.common import Conf, pretty
from obsoleta.errorcodes import ErrorCode
from obsoleta.package import Package
from obsoleta.obsoletacore import Obsoleta
from obsoleta.obsoleta_api import ObsoletaApi
from obsoleta.exceptions import ObsoletaException

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
parser.add_argument('--key',
                    help='multislot key to use. See also --keypath.')
parser.add_argument('--keypath',
                    help='path to multislot key file to use. See also --key.')

parser.add_argument('--check', action='store_true',
                    help='command: check a specified package')
parser.add_argument('--tree', action='store_true',
                    help='command: show tree for a package')
parser.add_argument('--buildorder', action='store_true',
                    help='command: show dependencies in building order for a package')
parser.add_argument('--listmissing', action='store_true',
                    help='command: list missing packages in --package dependency tree')
parser.add_argument('--upstream', action='store_true',
                    help='command: get the paths for the packages matching --package. Notice that the "last package '
                         'for an end-artifact" will itself be an upsteam package which can be slightly confusing')
parser.add_argument('--downstream', action='store_true',
                    help='command: get the paths for packages using the package given with --package')
parser.add_argument('--printarchs', action='store_true',
                    help='command: print the name of all found architectures')
parser.add_argument('--print', action='store_true',
                    help='command: like buildorder but print as a package json. See also dixi --print.')
parser.add_argument('--digraph', action='store_true',
                    help='command: make dependency plot for the package given with --package')

parser.add_argument('--bumpdirect', action='store_true',
                    help='command: bump the version for --package but only where explicitly referenced, '
                         'see also bump. Requires --version.')
parser.add_argument('--bump', action='store_true',
                    help='command: bump the version for --package where downstreams also get bumped recursively, '
                         'see also bumpdirect. Requires --version.')
parser.add_argument('--version',
                    help='the new version x.y.z, used with --bump')
parser.add_argument('--dryrun', action='store_true',
                    help='do not actually modify any package files for --bump')
parser.add_argument('--nnl', action='store_true',
                    help='do not append the last newline in text output')
parser.add_argument('--skip_bumping_ranged_versions', action='store_true',
                    help='still evaluating this one. Added here for testing...')
parser.add_argument('--keeptrack', action='store_true',
                    help='require that tracks are alike and refuse to "upgrade" them')

parser.add_argument('--printpaths', action='store_true',
                    help='print package paths rather than the compressed form')

parser.add_argument('--conf', dest='conffile',
                    help='load specified configuration file rather than the default obsoleta.conf. Use "default" '
                         'to use the built-in default configuration')
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
    set_log_level(verbose=True)
elif args.info:
    set_log_level(info=True)

valid_package_command = (args.tree or args.check or args.buildorder or args.listmissing or args.print or
                        args.upstream or args.downstream or args.bumpdirect or args.bump or args.digraph)

# commands that needs no package defined
valid_non_package_command = args.dumpcache or args.printarchs

valid_command = valid_package_command or valid_non_package_command

if args.clearcache:
    # clearcache can be used as standalone command
    try:
        os.remove(Obsoleta.default_cache_filename())
        inf(f'cache cleared ({Obsoleta.default_cache_filename()})')
    except:
        err('cache not found')
    if not valid_command:
        # clearcache was a standalone invocation, we're good
        exit(0)

# go-no-go checks

if not valid_command:
    err('no action specified (--check, --tree, --buildorder, --listmissing, --upstream,'
        ' --downstream --printarchs --bumpdirect --bump --dumpcache --print')
    exit(ErrorCode.MISSING_INPUT.value)

if valid_package_command and not args.package and not args.path:
    err('no package specified (use --package for compact form or --path for package dir)')
    exit(ErrorCode.MISSING_INPUT.value)

# parse configuration file

conf = Conf(args.conffile)

if args.depth:
    # a depth given on the commandline overrules any depth there might have been in the configuration file
    conf.depth = int(args.depth)

if args.keeptrack:
    conf.keep_track = int(args.keeptrack)

if args.keepgoing:
    conf.keepgoing = True

conf.dump()
exit_code = ErrorCode.OK

# construct obsoleta, load and parse everything in one go

try:
    obsoleta = ObsoletaApi(conf, args)

    if valid_package_command:
        if args.path:
            try:
                package = Package.construct_from_package_path(
                    conf, args.path, key=args.key, keypath=args.keypath)
            except FileNotFoundError as e:
                err(str(e))
                exit(ErrorCode.PACKAGE_NOT_FOUND.value)
        else:
            package = Package.construct_from_compact(conf, args.package)

except ObsoletaException as e:
    err(f'Exception {e.ErrorCode.name}: {str(e)}')
    exit_code = e.ErrorCode
except Exception as e:
    err(f'caught unexpected exception: {str(e)}')
    if args.verbose:
        print(traceback.format_exc())
    exit(ErrorCode.UNKNOWN_EXCEPTION.value)

newline = not args.nnl

# and now figure out what to do
try:
    if exit_code != ErrorCode.OK:
        pass

    elif args.dumpcache:
        exit_code = ErrorCode.OK
        print_result_nl(json.dumps(obsoleta.serialize(), indent=4))

    elif args.check:
        deb(f'checking package "{package}"')
        error, errors = obsoleta.get_errors(package)

        if error.get_errorcode() == ErrorCode.PACKAGE_NOT_FOUND:
            err(error.get_message())
            exit_code = error.get_errorcode()
        elif error.has_error() or errors:
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
            print_result("\n".join(result), newline)
        else:
            err(error.print())
            exit_code = error.get_errorcode()

    elif args.buildorder:
        exit_code = ErrorCode.OK
        deb('packages listed in buildorder')
        errors, resolved = obsoleta.buildorder(package)

        if errors[0].has_error():
            for error in errors:
                err(error.get_message())
            exit_code = errors[0].get_errorcode()
        else:
            for _package in resolved:
                if args.printpaths:
                    print_result(_package.get_path(), True)
                else:
                    print_result(_package.to_string(), True)

                _errors = _package.get_errors()
                if _errors:
                    for _error in _errors:
                        exit_code = _error.get_errorcode()
                        err(' - error: ' + _error.to_string())

    elif args.print:
        error, jsn = obsoleta.print(package)
        if error.is_ok():
            print(pretty(jsn))
        exit_code = error.get_errorcode()

    elif args.listmissing:
        exit_code = ErrorCode.OK
        deb('list any missing packages for %s' % package)
        error, missing_list = obsoleta.list_missing(package)
        for missing in missing_list:
            print(missing.to_string())

    elif args.printarchs:
        exit_code = ErrorCode.OK
        error, archs = obsoleta.get_all_archs()
        for arch in archs:
            print(arch)

    elif args.upstream:
        error, lookup = obsoleta.upstreams(package)
        if error.is_ok():
            print_result("\n".join(p.get_path() for p in lookup), newline)
            exit_code = ErrorCode.OK
        else:
            err('unable to locate upstream %s' % package)
            exit_code = ErrorCode.PACKAGE_NOT_FOUND

    elif args.downstream:
        error, lookup = obsoleta.downstreams(package)
        if error.is_ok():
            print_result("\n".join(p.get_path() for p in lookup), newline)
            exit_code = ErrorCode.OK
        else:
            err('unable to locate downstream %s' % package)
            exit_code = ErrorCode.PACKAGE_NOT_FOUND

    elif args.dumpcache:
        pass

    elif args.bumpdirect or args.bump:
        if not args.version:
            exit_code = ErrorCode.MISSING_INPUT
        else:
            error, messages = obsoleta.bump(package, args.version, args.bump, args.dryrun, indent_messages=True)
            if error.is_ok():
                print_result_nl("\n".join(line for line in messages))
                exit_code = ErrorCode.OK
            else:
                err(error.get_message())
                exit_code = error.get_errorcode()

    elif args.digraph:
        obsoleta.generate_digraph(package)

    else:
        err("no valid command found")

    if exit_code != ErrorCode.OK:
        print()
        err('failed with error %i: %s' % (exit_code.value, ErrorCode.to_string(exit_code.value)))

    if args.yappi:
        yappirun.stop_yappi()

    exit(exit_code.value)

except Exception as e:
    err(f'command gave unexpected exception: {str(e)}')
    if args.verbose or args.info:
        print(traceback.format_exc())
    exit(ErrorCode.UNKNOWN_EXCEPTION.value)
