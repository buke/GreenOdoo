import xml.dom.minidom
domimpl = xml.dom.minidom.getDOMImplementation()

import sys
import string
import urlparse
import urllib
from StringIO import StringIO

import utils
from constants import COLLECTION, OBJECT, DAV_PROPS, RT_ALLPROP, RT_PROPNAME, RT_PROP
from errors import *
from utils import create_treelist, quote_uri, gen_estring

class COPY:
    """ copy resources and eventually create multistatus responses

    This module implements the COPY class which is responsible for
    copying resources. Usually the normal copy work is done in the
    interface class. This class only creates error messages if error
    occur.

    """


    def __init__(self,dataclass,src_uri,dst_uri,overwrite):
        self.__dataclass=dataclass
        self.__src=src_uri
        self.__dst=dst_uri
        self.__overwrite=overwrite


    def single_action(self):
        """ copy a normal resources.

        We try to copy it and return the result code.
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

        return dc.copyone(self.__src,self.__dst,self.__overwrite)

        #return copyone(dc,self.__src,self.__dst,self.__overwrite)

    def tree_action(self):
        """ copy a tree of resources (a collection)

        Here we return a multistatus xml element.

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
        
        
        result=dc.copytree(self.__src,self.__dst,self.__overwrite)
        #result=copytree(dc,self.__src,self.__dst,self.__overwrite)

        if not result: return None

        ###
        ### create the multistatus XML element
        ### (this is also the same as in delete.py.
        ###  we might make a common method out of it)
        ###

        doc = domimpl.createDocument(None, "D:multistatus", None)
        doc.documentElement.setAttribute("xmlns:D","DAV:")

        for el,ec in result.items():
                re=doc.createElement("D:response")
                hr=doc.createElement("D:href")
                st=doc.createElement("D:status")
                huri=doc.createTextNode(quote_uri(el))
                t=doc.createTextNode(gen_estring(ec))
                st.appendChild(t)
                hr.appendChild(huri)
                re.appendChild(hr)
                re.appendChild(st)
                ms.appendChild(re)

        return doc.toxml(encoding="utf-8")
