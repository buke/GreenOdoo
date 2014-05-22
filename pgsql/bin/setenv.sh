#!/bin/sh
PGBINDIR=$(dirname $0)
BASEPATH=$PGBINDIR/../..

LD_LIBRARY_PATH="$BASEPATH/pgsql/lib:$BASEPATH/common/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH
DYLD_LIBRARY_PATH="$BASEPATH/pgsql/lib:$DYLD_LIBRARY_PATH"
export DYLD_LIBRARY_PATH
LC_MESSAGES=C
export LC_MESSAGES
        
PGDATA="$BASEPATH/pgsql/data"
export PGDATA

find $PGDATA -type f|xargs chmod 600
find $PGDATA -type d|xargs chmod 700
