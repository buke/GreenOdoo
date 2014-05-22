import xml.dom.minidom
domimpl = xml.dom.minidom.getDOMImplementation()

import logging
import urlparse
import urllib

import utils
from constants import RT_ALLPROP, RT_PROPNAME, RT_PROP
from errors import DAV_Error, DAV_NotFound

log = logging.getLogger(__name__)


class PROPFIND:
    """ parse a propfind xml element and extract props

    It will set the following instance vars:

    request_class   : ALLPROP | PROPNAME | PROP
    proplist    : list of properties
    nsmap       : map of namespaces

    The list of properties will contain tuples of the form
    (element name, ns_prefix, ns_uri)


    """

    def __init__(self, uri, dataclass, depth, body):
        self.request_type = None
        self.nsmap = {}
        self.proplist = {}
        self.default_ns = None
        self._dataclass = dataclass
        self._depth = str(depth)
        self._uri = uri.rstrip('/')
        self._has_body = None   # did we parse a body?

        if dataclass.verbose:
            log.info('PROPFIND: Depth is %s, URI is %s' % (depth, uri))

        if body:
            self.request_type, self.proplist, self.namespaces = \
                utils.parse_propfind(body)
            self._has_body = True

    def createResponse(self):
        """ Create the multistatus response

        This will be delegated to the specific method
        depending on which request (allprop, propname, prop)
        was found.

        If we get a PROPNAME then we simply return the list with empty
        values which we get from the interface class

        If we get an ALLPROP we first get the list of properties and then
        we do the same as with a PROP method.

        """

        # check if resource exists
        if not self._dataclass.exists(self._uri):
            raise DAV_NotFound

        df = None
        if self.request_type == RT_ALLPROP:
            df = self.create_allprop()

        if self.request_type == RT_PROPNAME:
            df = self.create_propname()

        if self.request_type == RT_PROP:
            df = self.create_prop()

        if df != None:
            return df

        # no body means ALLPROP!
        df = self.create_allprop()
        return df

    def create_propname(self):
        """ create a multistatus response for the prop names """

        dc = self._dataclass
        # create the document generator
        doc = domimpl.createDocument(None, "multistatus", None)
        ms = doc.documentElement
        ms.setAttribute("xmlns:D", "DAV:")
        ms.tagName = 'D:multistatus'

        if self._depth == "0":
            pnames = dc.get_propnames(self._uri)
            re = self.mk_propname_response(self._uri, pnames, doc)
            ms.appendChild(re)

        elif self._depth == "1":
            pnames = dc.get_propnames(self._uri)
            re = self.mk_propname_response(self._uri, pnames, doc)
            ms.appendChild(re)

            for newuri in dc.get_childs(self._uri):
                pnames = dc.get_propnames(newuri)
                re = self.mk_propname_response(newuri, pnames, doc)
                ms.appendChild(re)
        elif self._depth == 'infinity':
            uri_list = [self._uri]
            while uri_list:
                uri = uri_list.pop()
                pnames = dc.get_propnames(uri)
                re = self.mk_propname_response(uri, pnames, doc)
                ms.appendChild(re)
                uri_childs = self._dataclass.get_childs(uri)
                if uri_childs:
                    uri_list.extend(uri_childs)

        return doc.toxml(encoding="utf-8")

    def create_allprop(self):
        """ return a list of all properties """
        self.proplist = {}
        self.namespaces = []
        for ns, plist in self._dataclass.get_propnames(self._uri).items():
            self.proplist[ns] = plist
            self.namespaces.append(ns)

        return self.create_prop()

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

        if self._depth == "0":
            gp, bp = self.get_propvalues(self._uri)
            res = self.mk_prop_response(self._uri, gp, bp, doc)
            ms.appendChild(res)

        elif self._depth == "1":
            gp, bp = self.get_propvalues(self._uri)
            res = self.mk_prop_response(self._uri, gp, bp, doc)
            ms.appendChild(res)

            for newuri in self._dataclass.get_childs(self._uri):
                gp, bp = self.get_propvalues(newuri)
                res = self.mk_prop_response(newuri, gp, bp, doc)
                ms.appendChild(res)
        elif self._depth == 'infinity':
            uri_list = [self._uri]
            while uri_list:
                uri = uri_list.pop()
                gp, bp = self.get_propvalues(uri)
                res = self.mk_prop_response(uri, gp, bp, doc)
                ms.appendChild(res)
                uri_childs = self._dataclass.get_childs(uri)
                if uri_childs:
                    uri_list.extend(uri_childs)

        return doc.toxml(encoding="utf-8")

    def mk_propname_response(self, uri, propnames, doc):
        """ make a new <prop> result element for a PROPNAME request

        This will simply format the propnames list.
        propnames should have the format {NS1 : [prop1, prop2, ...], NS2: ...}

        """
        re = doc.createElement("D:response")

        if self._dataclass.baseurl:
            uri = self._dataclass.baseurl + '/' + '/'.join(uri.split('/')[3:])

        # write href information
        uparts = urlparse.urlparse(uri)
        fileloc = uparts[2]
        href = doc.createElement("D:href")

        huri = doc.createTextNode(uparts[0] + '://' +
                                  '/'.join(uparts[1:2]) +
                                  urllib.quote(fileloc))
        href.appendChild(huri)
        re.appendChild(href)

        ps = doc.createElement("D:propstat")
        nsnum = 0

        for ns, plist in propnames.items():
            # write prop element
            pr = doc.createElement("D:prop")
            nsp = "ns" + str(nsnum)
            pr.setAttribute("xmlns:" + nsp, ns)
            nsnum += 1

            # write propertynames
            for p in plist:
                pe = doc.createElement(nsp + ":" + p)
                pr.appendChild(pe)

            ps.appendChild(pr)
        re.appendChild(ps)

        return re

    def mk_prop_response(self, uri, good_props, bad_props, doc):
        """ make a new <prop> result element

        We differ between the good props and the bad ones for
        each generating an extra <propstat>-Node (for each error
        one, that means).

        """
        re = doc.createElement("D:response")
        # append namespaces to response
        nsnum = 0
        for nsname in self.namespaces:
            if nsname != 'DAV:':
                re.setAttribute("xmlns:ns" + str(nsnum), nsname)
            nsnum += 1

        if self._dataclass.baseurl:
            uri = self._dataclass.baseurl + '/' + '/'.join(uri.split('/')[3:])

        # write href information
        uparts = urlparse.urlparse(uri)
        fileloc = uparts[2]
        href = doc.createElement("D:href")

        huri = doc.createTextNode(uparts[0] + '://' +
                                  '/'.join(uparts[1:2]) +
                                  urllib.quote(fileloc))
        href.appendChild(huri)
        re.appendChild(href)

        # write good properties
        ps = doc.createElement("D:propstat")
        if good_props:
            re.appendChild(ps)

        gp = doc.createElement("D:prop")
        for ns in good_props.keys():
            if ns != 'DAV:':
                ns_prefix = "ns" + str(self.namespaces.index(ns)) + ":"
            else:
                ns_prefix = 'D:'
            for p, v in good_props[ns].items():

                pe = doc.createElement(ns_prefix + str(p))
                if isinstance(v, xml.dom.minidom.Element):
                    pe.appendChild(v)
                elif isinstance(v, list):
                    for val in v:
                        pe.appendChild(val)
                else:
                    if p == "resourcetype":
                        if v == 1:
                            ve = doc.createElement("D:collection")
                            pe.appendChild(ve)
                    else:
                        ve = doc.createTextNode(v)
                        pe.appendChild(ve)

                gp.appendChild(pe)

        ps.appendChild(gp)
        s = doc.createElement("D:status")
        t = doc.createTextNode("HTTP/1.1 200 OK")
        s.appendChild(t)
        ps.appendChild(s)
        re.appendChild(ps)

        # now write the errors!
        if len(bad_props.items()):

            # write a propstat for each error code
            for ecode in bad_props.keys():
                ps = doc.createElement("D:propstat")
                re.appendChild(ps)
                bp = doc.createElement("D:prop")
                ps.appendChild(bp)

                for ns in bad_props[ecode].keys():
                    if ns != 'DAV:':
                        ns_prefix = "ns" + str(self.namespaces.index(ns)) + ":"
                    else:
                        ns_prefix = 'D:'

                    for p in bad_props[ecode][ns]:
                        pe = doc.createElement(ns_prefix + str(p))
                        bp.appendChild(pe)

                s = doc.createElement("D:status")
                t = doc.createTextNode(utils.gen_estring(ecode))
                s.appendChild(t)
                ps.appendChild(s)
                re.appendChild(ps)

        # return the new response element
        return re

    def get_propvalues(self, uri):
        """ create lists of property values for an URI

        We create two lists for an URI: the properties for
        which we found a value and the ones for which we
        only got an error, either because they haven't been
        found or the user is not allowed to read them.

        """
        good_props = {}
        bad_props = {}

        ddc = self._dataclass
        for ns, plist in self.proplist.items():
            good_props[ns] = {}
            for prop in plist:
                ec = 0
                try:
                    r = ddc.get_prop(uri, ns, prop)
                    good_props[ns][prop] = r
                except DAV_Error, error_code:
                    ec = error_code[0]

                # ignore props with error_code if 0 (invisible)
                if ec == 0:
                    continue

                if ec in bad_props:
                    if ns in bad_props[ec]:
                        bad_props[ec][ns].append(prop)
                    else:
                        bad_props[ec][ns] = [prop]
                else:
                    bad_props[ec] = {ns: [prop]}

        return good_props, bad_props
