import os
import sys
import time
import socket
import string
import posixpath
import base64
import urlparse
import urllib
import random

import logging

log = logging.getLogger(__name__)

import xml.dom
from xml.dom import minidom

from utils import rfc1123_date, IfParser, tokenFinder
from string import atoi,split
from errors import *

tokens_to_lock = {}
uris_to_token = {}

class LockManager:
    """ Implements the locking backend and serves as MixIn for DAVRequestHandler """

    def _init_locks(self):
        return tokens_to_lock, uris_to_token

    def _l_isLocked(self, uri):
        tokens, uris = self._init_locks()
        return uris.has_key(uri)

    def _l_hasLock(self, token):
        tokens, uris = self._init_locks()
        return tokens.has_key(token)

    def _l_getLockForUri(self, uri):
        tokens, uris = self._init_locks()
        return uris.get(uri, None)

    def _l_getLock(self, token):
        tokens, uris = self._init_locks()
        return tokens.get(token, None)

    def _l_delLock(self, token):
        tokens, uris = self._init_locks()
        if tokens.has_key(token):
            del uris[tokens[token].uri]
            del tokens[token]

    def _l_setLock(self, lock):
        tokens, uris = self._init_locks()
        tokens[lock.token] = lock
        uris[lock.uri] = lock

    def _lock_unlock_parse(self, body):
        doc = minidom.parseString(body)

        data = {}
        info = doc.getElementsByTagNameNS('DAV:', 'lockinfo')[0]
        data['lockscope'] = info.getElementsByTagNameNS('DAV:', 'lockscope')[0]\
                                .firstChild.localName
        data['locktype'] = info.getElementsByTagNameNS('DAV:', 'locktype')[0]\
                                .firstChild.localName
        data['lockowner'] = info.getElementsByTagNameNS('DAV:', 'owner')
        return data

    def _lock_unlock_create(self, uri, creator, depth, data):
        lock = LockItem(uri, creator, **data)
        iscollection = uri[-1] == '/' # very dumb collection check

        result = ''
        if depth == 'infinity' and iscollection:
            # locking of children/collections not yet supported
            pass

        if not self._l_isLocked(uri):
            self._l_setLock(lock)

        # because we do not handle children we leave result empty
        return lock.token, result

    def do_UNLOCK(self):
        """ Unlocks given resource """

        dc = self.IFACE_CLASS

        if self._config.DAV.getboolean('verbose') is True:
            log.info('UNLOCKing resource %s' % self.headers)

        uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri = urllib.unquote(uri)

        # check lock token - must contain a dash
        if not self.headers.get('Lock-Token', '').find('-')>0:
            return self.send_status(400)

        token = tokenFinder(self.headers.get('Lock-Token'))
        if self._l_isLocked(uri):
            self._l_delLock(token)

        self.send_body(None, '204', 'Ok', 'Ok')

    def do_LOCK(self):
        """ Locking is implemented via in-memory caches. No data is written to disk.  """

        dc = self.IFACE_CLASS

        log.info('LOCKing resource %s' % self.headers)

        body = None
        if self.headers.has_key('Content-Length'):
            l = self.headers['Content-Length']
            body = self.rfile.read(atoi(l))

        depth = self.headers.get('Depth', 'infinity')

        uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri = urllib.unquote(uri)
        log.info('do_LOCK: uri = %s' % uri)

        ifheader = self.headers.get('If')
        alreadylocked = self._l_isLocked(uri)
        log.info('do_LOCK: alreadylocked = %s' % alreadylocked)

        if body and alreadylocked:
            # Full LOCK request but resource already locked
            self.responses[423] = ('Locked', 'Already locked')
            return self.send_status(423)

        elif body and not ifheader:
            # LOCK with XML information
            data = self._lock_unlock_parse(body)
            token, result = self._lock_unlock_create(uri, 'unknown', depth, data)

            if result:
                self.send_body(result, '207', 'Error', 'Error',
                                'text/xml; charset="utf-8"')

            else:
                lock = self._l_getLock(token)
                self.send_body(lock.asXML(), '200', 'OK', 'OK',
                                'text/xml; charset="utf-8"',
                                {'Lock-Token' : '<opaquelocktoken:%s>' % token})


        else:
            # refresh request - refresh lock timeout
            taglist = IfParser(ifheader)
            found = 0
            for tag in taglist:
                for listitem in tag.list:
                    token = tokenFinder(listitem)
                    if token and self._l_hasLock(token):
                        lock = self._l_getLock(token)
                        timeout = self.headers.get('Timeout', 'Infinite')
                        lock.setTimeout(timeout) # automatically refreshes
                        found = 1

                        self.send_body(lock.asXML(), 
                                        '200', 'OK', 'OK', 'text/xml; encoding="utf-8"')
                        break
                if found: 
                    break

            # we didn't find any of the tokens mentioned - means
            # that table was cleared or another error
            if not found:
                self.send_status(412) # precondition failed

class LockItem:
    """ Lock with support for exclusive write locks. Some code taken from
    webdav.LockItem from the Zope project. """

    def __init__(self, uri, creator, lockowner, depth=0, timeout='Infinite',
                    locktype='write', lockscope='exclusive', token=None, **kw):

        self.uri = uri
        self.creator = creator
        self.owner = lockowner
        self.depth = depth
        self.timeout = timeout
        self.locktype = locktype
        self.lockscope = lockscope
        self.token = token and token or self.generateToken()
        self.modified = time.time()

    def getModifiedTime(self):
        return self.modified

    def refresh(self):
        self.modified = time.time()

    def isValid(self):
        now = time.time()
        modified = self.modified
        timeout = self.timeout
        return (modified + timeout) > now

    def generateToken(self):
        _randGen = random.Random(time.time())
        return '%s-%s-00105A989226:%.03f' %  \
             (_randGen.random(),_randGen.random(),time.time())

    def getTimeoutString(self):
        t = str(self.timeout)
        if t[-1] == 'L': t = t[:-1]
        return 'Second-%s' % t

    def setTimeout(self, timeout):
        self.timeout = timeout
        self.modified = time.time()

    def asXML(self, namespace='d', discover=False):
        owner_str = ''
        if isinstance(self.owner, str):
            owner_str = self.owner
        elif isinstance(self.owner, xml.dom.minicompat.NodeList):
            owner_str = "".join([node.toxml() for node in self.owner[0].childNodes])

        token = self.token
        base = ('<%(ns)s:activelock>\n'
             '  <%(ns)s:locktype><%(ns)s:%(locktype)s/></%(ns)s:locktype>\n'
             '  <%(ns)s:lockscope><%(ns)s:%(lockscope)s/></%(ns)s:lockscope>\n'
             '  <%(ns)s:depth>%(depth)s</%(ns)s:depth>\n'
             '  <%(ns)s:owner>%(owner)s</%(ns)s:owner>\n'
             '  <%(ns)s:timeout>%(timeout)s</%(ns)s:timeout>\n'
             '  <%(ns)s:locktoken>\n'
             '   <%(ns)s:href>opaquelocktoken:%(locktoken)s</%(ns)s:href>\n'
             '  </%(ns)s:locktoken>\n'
             ' </%(ns)s:activelock>\n'
             ) % {
               'ns': namespace,
               'locktype': self.locktype,
               'lockscope': self.lockscope,
               'depth': self.depth,
               'owner': owner_str,
               'timeout': self.getTimeoutString(),
               'locktoken': token,
               }

        if discover is True:
            return base

        s = """<?xml version="1.0" encoding="utf-8" ?>
<d:prop xmlns:d="DAV:">
 <d:lockdiscovery>
  %s
 </d:lockdiscovery>
</d:prop>""" % base

        return s
