import sys
import urlparse
import os
import time
from string import joinfields, split, lower
import logging
import types
import shutil

from pywebdav.lib.constants import COLLECTION, OBJECT
from pywebdav.lib.errors import *
from pywebdav.lib.iface import *
from pywebdav.lib.davcmd import copyone, copytree, moveone, movetree, delone, deltree

log = logging.getLogger(__name__)

BUFFER_SIZE = 128 * 1000 
# include magic support to correctly determine mimetypes
MAGIC_AVAILABLE = False
try:
    import mimetypes
    MAGIC_AVAILABLE = True
    log.info('Mimetype support ENABLED')
except ImportError:
    log.info('Mimetype support DISABLED')
    pass

class Resource(object):
    # XXX this class is ugly
    def __init__(self, fp, file_size):
        self.__fp = fp
        self.__file_size = file_size

    def __len__(self):
        return self.__file_size

    def __iter__(self):
        while 1:
            data = self.__fp.read(BUFFER_SIZE)
            if not data:
                break
            yield data
            time.sleep(0.005)
        self.__fp.close()

    def read(self, length = 0):
        if length == 0:
            length = self.__file_size

        data = self.__fp.read(length)
        return data
        

class FilesystemHandler(dav_interface):
    """ 
    Model a filesystem for DAV

    This class models a regular filesystem for the DAV server

    The basic URL will be http://localhost/
    And the underlying filesystem will be /tmp

    Thus http://localhost/gfx/pix will lead
    to /tmp/gfx/pix

    """

    def __init__(self, directory, uri, verbose=False):
        self.setDirectory(directory)
        self.setBaseURI(uri)

        # should we be verbose?
        self.verbose = verbose
        log.info('Initialized with %s %s' % (directory, uri))

    def setDirectory(self, path):
        """ Sets the directory """

        if not os.path.isdir(path):
            raise Exception, '%s not must be a directory!' % path

        self.directory = path

    def setBaseURI(self, uri):
        """ Sets the base uri """

        self.baseuri = uri

    def uri2local(self,uri):
        """ map uri in baseuri and local part """

        uparts=urlparse.urlparse(uri)
        fileloc=uparts[2][1:]
        filename=os.path.join(self.directory,fileloc)
        filename=os.path.normpath(filename)
        return filename

    def local2uri(self,filename):
        """ map local filename to self.baseuri """

        pnum=len(split(self.directory.replace("\\","/"),"/"))
        parts=split(filename.replace("\\","/"),"/")[pnum:]
        sparts="/"+joinfields(parts,"/")
        uri=urlparse.urljoin(self.baseuri,sparts)
        return uri


    def get_childs(self, uri, filter=None):
        """ return the child objects as self.baseuris for the given URI """

        fileloc=self.uri2local(uri)
        filelist=[]

        if os.path.exists(fileloc):
            if os.path.isdir(fileloc):
                try:
                    files=os.listdir(fileloc)
                except:
                    raise DAV_NotFound

                for file in files:
                    newloc=os.path.join(fileloc,file)
                    filelist.append(self.local2uri(newloc))

                log.info('get_childs: Childs %s' % filelist)

        return filelist

    def get_data(self,uri, range = None):
        """ return the content of an object """

        path=self.uri2local(uri)
        if os.path.exists(path):
            if os.path.isfile(path):
                file_size = os.path.getsize(path)
                if range == None:
                    fp=open(path,"r")
                    log.info('Serving content of %s' % uri)
                    return Resource(fp, file_size)
                else:
                    if range[1] == '':
                        range[1] = file_size
                    else:
                        range[1] = int(range[1])

                    if range[0] == '':
                        range[0] = file_size - range[1]
                    else:
                        range[0] = int(range[0])

                    if range[0] > file_size:
                        raise DAV_Requested_Range_Not_Satisfiable

                    if range[1] > file_size:
                        range[1] = file_size

                    fp=open(path,"r")
                    fp.seek(range[0])
                    log.info('Serving range %s -> %s content of %s' % (range[0], range[1], uri))
                    return Resource(fp, range[1] - range[0])
            elif os.path.isdir(path):
                # GET for collections is defined as 'return s/th meaningful' :-)
                from StringIO import StringIO
                stio = StringIO('Directory at %s' % uri)
                return Resource(StringIO('Directory at %s' % uri), stio.len)
            else:
                # also raise an error for collections
                # don't know what should happen then..
                log.info('get_data: %s not found' % path)

        raise DAV_NotFound

    def _get_dav_resourcetype(self,uri):
        """ return type of object """
        path=self.uri2local(uri)
        if os.path.isfile(path):
            return OBJECT

        elif os.path.isdir(path):
            return COLLECTION

        raise DAV_NotFound

    def _get_dav_displayname(self,uri):
        raise DAV_Secret    # do not show

    def _get_dav_getcontentlength(self,uri):
        """ return the content length of an object """
        path=self.uri2local(uri)
        if os.path.exists(path):
            if os.path.isfile(path):
                s=os.stat(path)
                return str(s[6])

        return '0'

    def get_lastmodified(self,uri):
        """ return the last modified date of the object """
        path=self.uri2local(uri)
        if os.path.exists(path):
            s=os.stat(path)
            date=s[8]
            return date

        raise DAV_NotFound

    def get_creationdate(self,uri):
        """ return the last modified date of the object """
        path=self.uri2local(uri)
        if os.path.exists(path):
            s=os.stat(path)
            date=s[9]
            return date

        raise DAV_NotFound

    def _get_dav_getcontenttype(self,uri):
        """ find out yourself! """

        path=self.uri2local(uri)
        if os.path.exists(path):
            if os.path.isfile(path):
                if MAGIC_AVAILABLE is False \
                        or self.mimecheck is False:
                    return 'application/octet-stream'
                else:
                    ret, encoding = mimetypes.guess_type(path)

                    # for non mimetype related result we
                    # simply return an appropriate type
                    if ret.find('/')==-1:
                        if ret.find('text')>=0:
                            return 'text/plain'
                        else:
                            return 'application/octet-stream'
                    else:
                        return ret

            elif os.path.isdir(path):
                return "httpd/unix-directory"

        raise DAV_NotFound, 'Could not find %s' % path

    def put(self, uri, data, content_type=None):
        """ put the object into the filesystem """
        path=self.uri2local(uri)
        try:
            fp=open(path, "w+")
            if isinstance(data, types.GeneratorType):
                for d in data:
                    fp.write(d)
            else:
                if data:
                    fp.write(data)
            fp.close()
            log.info('put: Created %s' % uri)
        except:
            log.info('put: Could not create %s' % uri)
            raise DAV_Error, 424

        return None

    def mkcol(self,uri):
        """ create a new collection """
        path=self.uri2local(uri)

        # remove trailing slash
        if path[-1]=="/": path=path[:-1]

        # test if file already exists
        if os.path.exists(path):
            raise DAV_Error,405

        # test if parent exists
        h,t=os.path.split(path)
        if not os.path.exists(h):
            raise DAV_Error, 409

        # test, if we are allowed to create it
        try:
            os.mkdir(path)
            log.info('mkcol: Created new collection %s' % path)
            return 201
        except:
            log.info('mkcol: Creation of %s denied' % path)
            raise DAV_Forbidden

    ### ?? should we do the handler stuff for DELETE, too ?
    ### (see below)

    def rmcol(self,uri):
        """ delete a collection """
        path=self.uri2local(uri)
        if not os.path.exists(path):
            raise DAV_NotFound

        try:
            shutil.rmtree(path)
        except OSError:
            raise DAV_Forbidden # forbidden
        
        return 204

    def rm(self,uri):
        """ delete a normal resource """
        path=self.uri2local(uri)
        if not os.path.exists(path):
            raise DAV_NotFound

        try:
            os.unlink(path)
        except OSError, ex:
            log.info('rm: Forbidden (%s)' % ex)
            raise DAV_Forbidden # forbidden

        return 204

    ###
    ### DELETE handlers (examples)
    ### (we use the predefined methods in davcmd instead of doing
    ### a rm directly
    ###

    def delone(self,uri):
        """ delete a single resource

        You have to return a result dict of the form
        uri:error_code
        or None if everything's ok

        """
        return delone(self,uri)

    def deltree(self,uri):
        """ delete a collection 

        You have to return a result dict of the form
        uri:error_code
        or None if everything's ok
        """

        return deltree(self,uri)


    ###
    ### MOVE handlers (examples)
    ###

    def moveone(self,src,dst,overwrite):
        """ move one resource with Depth=0
        """

        return moveone(self,src,dst,overwrite)

    def movetree(self,src,dst,overwrite):
        """ move a collection with Depth=infinity
        """

        return movetree(self,src,dst,overwrite)

    ###
    ### COPY handlers
    ###

    def copyone(self,src,dst,overwrite):
        """ copy one resource with Depth=0
        """

        return copyone(self,src,dst,overwrite)

    def copytree(self,src,dst,overwrite):
        """ copy a collection with Depth=infinity
        """

        return copytree(self,src,dst,overwrite)

    ###
    ### copy methods.
    ### This methods actually copy something. low-level
    ### They are called by the davcmd utility functions
    ### copytree and copyone (not the above!)
    ### Look in davcmd.py for further details.
    ###

    def copy(self,src,dst):
        """ copy a resource from src to dst """

        srcfile=self.uri2local(src)
        dstfile=self.uri2local(dst)
        try:
            shutil.copy(srcfile, dstfile)
        except (OSError, IOError):
            log.info('copy: forbidden')
            raise DAV_Error, 409

    def copycol(self, src, dst):
        """ copy a collection.

        As this is not recursive (the davserver recurses itself)
        we will only create a new directory here. For some more
        advanced systems we might also have to copy properties from
        the source to the destination.
        """

        return self.mkcol(dst)

    def exists(self,uri):
        """ test if a resource exists """
        path=self.uri2local(uri)
        if os.path.exists(path):
            return 1
        return None

    def is_collection(self,uri):
        """ test if the given uri is a collection """
        path=self.uri2local(uri)
        if os.path.isdir(path):
            return 1
        else:
            return 0
