#!/bin/sh
PYBINDIR=$(dirname $0)
BASEDIR=$PYBINDIR/../..

PATH="${BASEDIR}/python/bin:${BASEDIR}/pgsql/bin:${BASEDIR}/common/bin:$PATH"
export PATH

LD_LIBRARY_PATH="${BASEDIR}/python/lib:${BASEDIR}/pgsql/lib:${BASEDIR}/common/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH

PYTHONPATH=${BASEDIR}/openerp:$PYTHONPATH
export PYTHONPATH

PYTHONHOME=${BASEDIR}/python
export PYTHONHOME

PYTHON_EGG_CACHE=${BASEDIR}/.tmp
export PYTHON_EGG_CACHE
