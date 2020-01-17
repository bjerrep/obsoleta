#!/bin/bash
set -e

if [ "$1" == "--help" ]; then
  echo "$0 'configuration_file' 'package_compact' 'action(including --)'"
  exit 0
fi

function exit_handler() {
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        eval echo "\'${BASH_COMMAND}\' gave exit code $exit_code"
        echo "$0 failed"
    else
        echo success
    fi
}

trap exit_handler EXIT

CONF=mini.conf
ROOT=$1
PACKAGE=$2
ACTION=$3

# First a quiet dry run. If something is wrong this should stop the script before
# it starts modifying files

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --check

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --locate |\
 xargs -I{} ./dixi.py --conf $CONF --path {} $ACTION --dryrun 1> /dev/null

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --upstream |\
 xargs -I{} ./dixi.py --conf $CONF --path {} --depends b $ACTION --dryrun 1> /dev/null

# And the real action goes here

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --locate |\
 xargs -I{} ./dixi.py --conf $CONF --path {} $ACTION

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --upstream |\
 xargs -I{} ./dixi.py --conf $CONF --path {} --depends b $ACTION

./obsoleta.py --conf $CONF --root $ROOT --package $PACKAGE --check
