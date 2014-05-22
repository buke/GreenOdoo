import sys
import string
import urlparse
import urllib
from StringIO import StringIO

import utils
from constants import COLLECTION, OBJECT, DAV_PROPS
from constants import RT_ALLPROP, RT_PROPNAME, RT_PROP
from errors import *
from utils import create_treelist, quote_uri, gen_estring, make_xmlresponse
from davcmd import moveone, movetree

class MOVE:
    """ move resources and eventually create multistatus responses

    This module implements the MOVE class which is responsible for
    moving resources.

    MOVE is implemented by a COPY followed by a DELETE of the old
    resource.

    """


    def __init__(self,dataclass,src_uri,dst_uri,overwrite):
        self.__dataclass=dataclass
        self.__src=src_uri
        self.__dst=dst_uri
        self.__overwrite=overwrite


    def single_action(self):
        """ move a normal resources.

        We try to move it and return the result code.
        This is for Depth==0

        """

        dc=self.__dataclass
        base=self.__src

        ### some basic tests
        # test if dest exists and overwrite is false
        if dc.exists(self.__dst) and not self.__overwrite: raise DAV_Error, 412
        # test if src and dst are the same
        # (we assume that both uris are on the same server!)
        ps=urlparse.urlparse(self.__src)[2]
        pd=urlparse.urlparse(self.__dst)[2]
        if ps==pd: raise DAV_Error, 403

        return dc.moveone(self.__src,self.__dst,self.__overwrite)

    def tree_action(self):
        """ move a tree of resources (a collection)

        Here we return a multistatus xml element.

        """
        dc=self.__dataclass
        base=self.__src

        ### some basic tests
        # test if dest exists and overwrite is false
        if dc.exists(self.__dst) and not self.__overwrite: raise DAV_Error,  412
        # test if src and dst are the same
        # (we assume that both uris are on the same server!)
        ps=urlparse.urlparse(self.__src)[2]
        pd=urlparse.urlparse(self.__dst)[2]
        if ps==pd: raise DAV_Error,  403

        result=dc.movetree(self.__src,self.__dst,self.__overwrite)
        if not result: return None

        # create the multistatus XML element
        return make_xmlresponse(result)

