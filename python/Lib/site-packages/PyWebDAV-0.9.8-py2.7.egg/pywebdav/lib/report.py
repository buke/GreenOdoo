from propfind import PROPFIND
from xml.dom import minidom
domimpl = minidom.getDOMImplementation()

from utils import get_parenturi

class REPORT(PROPFIND):

    def __init__(self, uri, dataclass, depth, body):
        PROPFIND.__init__(self, uri, dataclass, depth, body)

        doc = minidom.parseString(body)

        self.filter = doc.documentElement

    def create_propname(self):
        """ create a multistatus response for the prop names """

        dc=self._dataclass
        # create the document generator
        doc = domimpl.createDocument(None, "multistatus", None)
        ms = doc.documentElement
        ms.setAttribute("xmlns:D", "DAV:")
        ms.tagName = 'D:multistatus'

        if self._depth=="0":
            if self._uri in self._dataclass.get_childs(get_parenturi(self._uri),
                    self.filter):
                pnames=dc.get_propnames(self._uri)
                re=self.mk_propname_response(self._uri,pnames, doc)
                ms.appendChild(re)

        elif self._depth=="1":
            if self._uri in self._dataclass.get_childs(get_parenturi(self._uri),
                    self.filter):
                pnames=dc.get_propnames(self._uri)
                re=self.mk_propname_response(self._uri,pnames, doc)
                ms.appendChild(re)

            for newuri in dc.get_childs(self._uri, self.filter):
                pnames=dc.get_propnames(newuri)
                re=self.mk_propname_response(newuri,pnames, doc)
                ms.appendChild(re)
        elif self._depth=='infinity':
            uri_list = [self._uri]
            while uri_list:
                uri = uri_list.pop()
                if uri in self._dataclass.get_childs(get_parenturi(uri),
                        self.filter):
                    pnames=dc.get_propnames(uri)
                    re=self.mk_propname_response(uri,pnames, doc)
                    ms.appendChild(re)
                uri_childs = self._dataclass.get_childs(uri)
                if uri_childs:
                    uri_list.extend(uri_childs)

        return doc.toxml(encoding="utf-8")

    def create_prop(self):
        """ handle a <prop> request

        This will

        1. set up the <multistatus>-Framework

        2. read the property values for each URI 
           (which is dependant on the Depth header)
           This is done by the get_propvalues() method.

        3. For each URI call the append_result() method
           to append the actual <result>-Tag to the result
           document.

        We differ between "good" properties, which have been
        assigned a value by the interface class and "bad" 
        properties, which resulted in an error, either 404
        (Not Found) or 403 (Forbidden).

        """


        # create the document generator
        doc = domimpl.createDocument(None, "multistatus", None)
        ms = doc.documentElement
        ms.setAttribute("xmlns:D", "DAV:")
        ms.tagName = 'D:multistatus'

        if self._depth=="0":
            if self._uri in self._dataclass.get_childs(get_parenturi(self._uri),
                    self.filter):
                gp,bp=self.get_propvalues(self._uri)
                res=self.mk_prop_response(self._uri,gp,bp,doc)
                ms.appendChild(res)

        elif self._depth=="1":
            if self._uri in self._dataclass.get_childs(get_parenturi(self._uri),
                    self.filter):
                gp,bp=self.get_propvalues(self._uri)
                res=self.mk_prop_response(self._uri,gp,bp,doc)
                ms.appendChild(res)

            for newuri in self._dataclass.get_childs(self._uri, self.filter):
                gp,bp=self.get_propvalues(newuri)
                res=self.mk_prop_response(newuri,gp,bp,doc)
                ms.appendChild(res)
        elif self._depth=='infinity':
            uri_list = [self._uri]
            while uri_list:
                uri = uri_list.pop()
                if uri in self._dataclass.get_childs(get_parenturi(uri),
                        self.filter):
                    gp,bp=self.get_propvalues(uri)
                    res=self.mk_prop_response(uri,gp,bp,doc)
                    ms.appendChild(res)
                uri_childs = self._dataclass.get_childs(uri)
                if uri_childs:
                    uri_list.extend(uri_childs)

        return doc.toxml(encoding="utf-8")

