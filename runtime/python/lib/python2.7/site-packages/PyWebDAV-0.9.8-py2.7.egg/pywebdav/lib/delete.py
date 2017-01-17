import os
import string
import urllib
from StringIO import StringIO

from utils import gen_estring, quote_uri, make_xmlresponse
from davcmd import deltree

class DELETE:

    def __init__(self,uri,dataclass):
        self.__dataclass=dataclass
        self.__uri=uri

    def delcol(self):
        """ delete a collection """

        dc=self.__dataclass
        result=dc.deltree(self.__uri)

        if not len(result.items()):
            return None # everything ok

        # create the result element
        return make_xmlresponse(result)

    def delone(self):
        """ delete a resource """

        dc=self.__dataclass
        return dc.delone(self.__uri)

