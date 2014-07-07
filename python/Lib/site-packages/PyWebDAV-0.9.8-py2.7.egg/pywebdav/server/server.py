#!/usr/bin/env python

"""
Python WebDAV Server.

This is an example implementation of a DAVserver using the DAV package.

"""

import getopt, sys, os
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('pywebdav')

from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

try:
    import pywebdav.lib
except ImportError:
    print 'pywebdav.lib package not found! Please install into site-packages or set PYTHONPATH!'
    sys.exit(2)

from fileauth import DAVAuthHandler
from mysqlauth import MySQLAuthHandler
from fshandler import FilesystemHandler
from daemonize import startstop

from pywebdav.lib.INI_Parse import Configuration
from pywebdav.lib import VERSION, AUTHOR

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def runserver(
         port = 8008, host='localhost',
         directory='/tmp',
         verbose = False,
         noauth = False,
         user = '',
         password = '',
         handler = DAVAuthHandler,
         server = ThreadedHTTPServer):

    directory = directory.strip()
    directory = directory.rstrip('/')
    host = host.strip()

    if not os.path.isdir(directory):
        log.error('%s is not a valid directory!' % directory)
        return sys.exit(233)

    # basic checks against wrong hosts
    if host.find('/') != -1 or host.find(':') != -1:
        log.error('Malformed host %s' % host)
        return sys.exit(233)

    # no root directory
    if directory == '/':
        log.error('Root directory not allowed!')
        sys.exit(233)

    # dispatch directory and host to the filesystem handler
    # This handler is responsible from where to take the data
    handler.IFACE_CLASS = FilesystemHandler(directory, 'http://%s:%s/' % (host, port), verbose )

    # put some extra vars
    handler.verbose = verbose
    if noauth:
        log.warning('Authentication disabled!')
        handler.DO_AUTH = False

    log.info('Serving data from %s' % directory)

    if handler._config.DAV.getboolean('lockemulation') is False:
        log.info('Deactivated LOCK, UNLOCK (WebDAV level 2) support')

    handler.IFACE_CLASS.mimecheck = True
    if handler._config.DAV.getboolean('mimecheck') is False:
        handler.IFACE_CLASS.mimecheck = False
        log.info('Disabled mimetype sniffing (All files will have type application/octet-stream)')

    if handler._config.DAV.baseurl:
        log.info('Using %s as base url for PROPFIND requests' % handler._config.DAV.baseurl)
    handler.IFACE_CLASS.baseurl = handler._config.DAV.baseurl

    # initialize server on specified port
    runner = server( (host, port), handler )
    print('Listening on %s (%i)' % (host, port))

    try:
        runner.serve_forever()
    except KeyboardInterrupt:
        log.info('Killed by user')

usage = """PyWebDAV server (version %s)
Standalone WebDAV server

Make sure to activate LOCK, UNLOCK using parameter -J if you want
to use clients like Windows Explorer or Mac OS X Finder that expect
LOCK working for write support.

Usage: ./server.py [OPTIONS]
Parameters:
    -c, --config    Specify a file where configuration is specified. In this
                    file you can specify options for a running server.
                    For an example look at the config.ini in this directory.
    -D, --directory Directory where to serve data from
                    The user that runs this server must have permissions
                    on that directory. NEVER run as root!
                    Default directory is /tmp
    -B, --baseurl   Behind a proxy pywebdav needs to generate other URIs for PROPFIND.
                    If you are experiencing problems with links or such when behind
                    a proxy then just set this to a sensible default (e.g. http://dav.domain.com).
                    Make sure that you include the protocol.
    -H, --host      Host where to listen on (default: localhost)
    -P, --port      Port to bind server to  (default: 8008)
    -u, --user      Username for authentication
    -p, --password  Password for given user
    -n, --noauth    Pass parameter if server should not ask for authentication
                    This means that every user has access
    -m, --mysql     Pass this parameter if you want MySQL based authentication.
                    If you want to use MySQL then the usage of a configuration
                    file is mandatory.
    -J, --nolock    Deactivate LOCK and UNLOCK mode (WebDAV Version 2).
    -M, --nomime    Deactivate mimetype sniffing. Sniffing is based on magic numbers
                    detection but can be slow under heavy load. If you are experiencing
                    speed problems try to use this parameter.
    -T, --noiter    Deactivate iterator. Use this if you encounter file corruption during 
                    download. Also disables chunked body response.
    -i, --icounter  If you want to run multiple instances then you have to
                    give each instance it own number so that logfiles and such
                    can be identified. Default is 0
    -d, --daemon    Make server act like a daemon. That means that it is going
                    to background mode. All messages are redirected to
                    logfiles (default: /tmp/pydav.log and /tmp/pydav.err).
                    You need to pass one of the following values to this parameter
                        start   - Start daemon
                        stop    - Stop daemon
                        restart - Restart complete server
                        status  - Returns status of server

    -v, --verbose   Be verbose.
    -l, --loglevel  Select the log level : DEBUG, INFO, WARNING, ERROR, CRITICAL
                    Default is WARNING
    -h, --help      Show this screen

Please send bug reports and feature requests to %s
""" % (VERSION, AUTHOR)

def setupDummyConfig(**kw):

    class DummyConfigDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

        def getboolean(self, name):
            return (str(getattr(self, name, 0)) in ('1', "yes", "true", "on", "True"))

    class DummyConfig:
        DAV = DummyConfigDAV(**kw)

    return DummyConfig()

def run():
    verbose = False
    directory = '/tmp'
    port = 8008
    host = 'localhost'
    noauth = False
    user = ''
    password = ''
    daemonize = False
    daemonaction = 'start'
    counter = 0
    mysql = False
    lockemulation = True
    http_response_use_iterator = True
    chunked_http_response = True
    configfile = ''
    mimecheck = True
    loglevel = 'warning'
    baseurl = ''

    # parse commandline
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'P:D:H:d:u:p:nvhmJi:c:Ml:TB:',
                ['host=', 'port=', 'directory=', 'user=', 'password=',
                 'daemon=', 'noauth', 'help', 'verbose', 'mysql', 
                 'icounter=', 'config=', 'nolock', 'nomime', 'loglevel', 'noiter',
                 'baseurl='])
    except getopt.GetoptError, e:
        print usage
        print '>>>> ERROR: %s' % str(e)
        sys.exit(2)

    for o,a in opts:
        if o in ['-i', '--icounter']:
            counter = int(str(a).strip())

        if o in ['-m', '--mysql']:
            mysql = True

        if o in ['-M', '--nomime']:
            mimecheck = False

        if o in ['-J', '--nolock']:
            lockemulation = False

        if o in ['-T', '--noiter']:
            http_response_use_iterator = False
            chunked_http_response = False

        if o in ['-c', '--config']:
            configfile = a

        if o in ['-D', '--directory']:
            directory = a

        if o in ['-H', '--host']:
            host = a

        if o in ['-P', '--port']:
            port = a

        if o in ['-v', '--verbose']:
            verbose = True

        if o in ['-l', '--loglevel']:
            loglevel = a.lower()

        if o in ['-h', '--help']:
            print usage
            sys.exit(2)

        if o in ['-n', '--noauth']:
            noauth = True

        if o in ['-u', '--user']:
            user = a

        if o in ['-p', '--password']:
            password = a

        if o in ['-d', '--daemon']:
            daemonize = True
            daemonaction = a

        if o in ['-B', '--baseurl']:
            baseurl = a.lower()

    # This feature are disabled because they are unstable
    http_request_use_iterator = 0

    conf = None
    if configfile != '':
        log.info('Reading configuration from %s' % configfile)
        conf = Configuration(configfile)

        dv = conf.DAV
        verbose = bool(int(dv.verbose))
        loglevel = dv.get('loglevel', loglevel).lower()
        directory = dv.directory
        port = dv.port
        host = dv.host
        noauth = bool(int(dv.noauth))
        user = dv.user
        password = dv.password
        daemonize = bool(int(dv.daemonize))
        if daemonaction != 'stop':
            daemonaction = dv.daemonaction
        counter = int(dv.counter)
        lockemulation = dv.lockemulation
        mimecheck = dv.mimecheck

        if 'chunked_http_response' not in dv:
            dv.set('chunked_http_response', chunked_http_response)

        if 'http_request_use_iterator' not in dv:
            dv.set('http_request_use_iterator', http_request_use_iterator)

        if 'http_response_use_iterator' not in dv:
            dv.set('http_response_use_iterator', http_response_use_iterator)

    else:

        _dc = { 'verbose' : verbose,
                'directory' : directory,
                'port' : port,
                'host' : host,
                'noauth' : noauth,
                'user' : user,
                'password' : password,
                'daemonize' : daemonize,
                'daemonaction' : daemonaction,
                'counter' : counter,
                'lockemulation' : lockemulation,
                'mimecheck' : mimecheck,
                'chunked_http_response': chunked_http_response,
                'http_request_use_iterator': http_request_use_iterator,
                'http_response_use_iterator': http_response_use_iterator,
                'baseurl' : baseurl
                }

        conf = setupDummyConfig(**_dc)

    if verbose and (LEVELS[loglevel] > LEVELS['info']):
        loglevel = 'info'

    logging.getLogger().setLevel(LEVELS[loglevel])

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

    if mysql == True and configfile == '':
        log.error('You can only use MySQL with configuration file!')
        sys.exit(3)

    if daemonaction != 'stop':
        log.info('Starting up PyWebDAV server (version %s)' % VERSION)
    else:
        log.info('Stopping PyWebDAV server (version %s)' % VERSION)

    if not noauth and daemonaction not in ['status', 'stop']:
        if not user:
            print usage
            print >>sys.stderr, '>> ERROR: No parameter specified!'
            print >>sys.stderr, '>> Example: davserver -D /tmp -n'
            sys.exit(3)

    if daemonaction == 'status':
        log.info('Checking for state...')

    if type(port) == type(''):
        port = int(port.strip())

    log.info('chunked_http_response feature %s' % (conf.DAV.getboolean('chunked_http_response') and 'ON' or 'OFF' ))
    log.info('http_request_use_iterator feature %s' % (conf.DAV.getboolean('http_request_use_iterator') and 'ON' or 'OFF' ))
    log.info('http_response_use_iterator feature %s' % (conf.DAV.getboolean('http_response_use_iterator') and 'ON' or 'OFF' ))
 
    if daemonize:

        # check if pid file exists
        if os.path.exists('/tmp/pydav%s.pid' % counter) and daemonaction not in ['status', 'stop']:
            log.error(
                  'Found another instance! Either use -i to specifiy another instance number or remove /tmp/pydav%s.pid!' % counter)
            sys.exit(3)

        startstop(stdout='/tmp/pydav%s.log' % counter, 
                    stderr='/tmp/pydav%s.err' % counter, 
                    pidfile='/tmp/pydav%s.pid' % counter, 
                    startmsg='>> Started PyWebDAV (PID: %s)',
                    action=daemonaction)

    # start now
    handler = DAVAuthHandler
    if mysql == True:
        handler = MySQLAuthHandler

    # injecting options
    handler._config = conf

    runserver(port, host, directory, verbose, noauth, user, password, 
              handler=handler)

if __name__ == '__main__':
    run()
