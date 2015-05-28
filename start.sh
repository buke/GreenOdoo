#!/bin/sh

#BASEDIR=$(dirname $0)
BASEDIR=$(dirname "$(readlink -f "$0")")

# set path
PATH="${BASEDIR}/runtime/python/bin:${BASEDIR}/runtime/pgsql/bin:${BASEDIR}/runtime/common/bin:$PATH"
export PATH

LD_LIBRARY_PATH="${BASEDIR}/runtime/python/lib:${BASEDIR}/runtime/pgsql/lib:${BASEDIR}/runtime/common/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH

# start postgres
./runtime/pgsql/bin/pg_ctl -D ./runtime/pgsql/data start

# start odoo
./runtime/python/bin/python ./source/openerp-server -c ./openerp-server.conf
