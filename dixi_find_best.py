#!/usr/bin/env python3
from log import err, logger
from common import Setup
from package import Package
from errorcodes import ErrorCode
import logging, argparse, os

# ---------------------------------------------------------------------------------------------


def find_best_candidate(setup, package, candidates):
    candidates = [x.strip() for x in candidates]
    candidates = [os.path.splitext(x)[0] for x in candidates]
    matches = []

    for i in candidates:
        can = Package.construct_from_compact(setup, i)
        if package == can:
            matches.append(can)

    if not matches:
        raise Exception(f'no matches found for {args.compact}')

    matches.sort(key=lambda caa: caa.get_version())
    return matches[-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser('dixi_find_best', description='''
        locate the best match from a list of candidates
        ''')
    parser.add_argument('--compact',
                        help='the package to satisfy')
    parser.add_argument('--conf', dest='conffile',
                        help='load specified configuration file rather than the default obsoleta.conf')

    parser.add_argument('--verbose', action='store_true',
                        help='enable all log messages')
    parser.add_argument('--info', action='store_true',
                        help='enable informational log messages')
    parser.add_argument('--keypath',
                        help='the relative keypath (directory name) to use for a multislotted package if a specific'
                             'slot needs to get resolved. See also --key.')
    parser.add_argument('--key',
                        help='the key to use for a multislotted package if a specific slot needs to get resolved. '
                             'See also --keypath.')
    parser.add_argument('--depends',
                        help='target is the package in the depends section with the name given with --depends')
    parser.add_argument('--candidate_file',
                        help='file with candidates to check')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.info:
        logger.setLevel(logging.INFO)

    setup = Setup(args.conffile)
    try:
        package = Package.construct_from_compact(setup, args.compact)

        with open(args.candidate_file) as f:
            candidates = f.readlines()

        candidate = find_best_candidate(setup, package, candidates)
        print(candidate)

    except Exception as e:
        err(str(e))
        exit(ErrorCode.PACKAGE_NOT_FOUND.value)

    exit(ErrorCode.OK.value)
