import time
import re

from xml.dom import minidom

import urlparse
from string import lower, split, atoi, joinfields
from StringIO import StringIO

from constants import RT_ALLPROP, RT_PROPNAME, RT_PROP
from BaseHTTPServer import BaseHTTPRequestHandler

def gen_estring(ecode):
    """ generate an error string from the given code """
    ec=atoi(str(ecode))
    if BaseHTTPRequestHandler.responses.has_key(ec):
        return "HTTP/1.1 %s %s" %(ec, BaseHTTPRequestHandler.responses[ec][0])
    else:
        return "HTTP/1.1 %s" %(ec)

def parse_propfind(xml_doc):
    """ 
    Parse an propfind xml file and return a list of props 
    """

    doc = minidom.parseString(xml_doc)

    request_type=None
    props={}
    namespaces=[]

    if doc.getElementsByTagNameNS("DAV:", "allprop"):
        request_type = RT_ALLPROP
    elif doc.getElementsByTagNameNS("DAV:", "propname"):
        request_type = RT_PROPNAME
    else:
        request_type = RT_PROP
        for i in doc.getElementsByTagNameNS("DAV:", "prop"):
            for e in i.childNodes:
                if e.nodeType != minidom.Node.ELEMENT_NODE:
                    continue
                ns = e.namespaceURI
                ename = e.localName
                if props.has_key(ns):
                    props[ns].append(ename)
                else:
                    props[ns]=[ename]
                    namespaces.append(ns)

    return request_type,props,namespaces


def create_treelist(dataclass,uri):
    """ create a list of resources out of a tree 

    This function is used for the COPY, MOVE and DELETE methods

    uri - the root of the subtree to flatten

    It will return the flattened tree as list

    """
    queue=[uri]
    list=[uri]
    while len(queue):
        element=queue[-1]
        if dataclass.is_collection(element):
            childs=dataclass.get_childs(element)
        else:
            childs=[]
        if len(childs):
            list=list+childs
        # update queue
        del queue[-1]
        if len(childs):
            queue=queue+childs
    return list

def is_prefix(uri1,uri2):
    """ returns 1 of uri1 is a prefix of uri2 """
    if uri2[:len(uri1)]==uri1:
        return 1
    else:
        return None

def quote_uri(uri):
    """ quote an URL but not the protocol part """
    import urlparse
    import urllib

    up=urlparse.urlparse(uri)
    np=urllib.quote(up[2])
    return urlparse.urlunparse((up[0],up[1],np,up[3],up[4],up[5]))

def get_uriparentpath(uri):
    """ extract the uri path and remove the last element """
    up=urlparse.urlparse(uri)
    return joinfields(split(up[2],"/")[:-1],"/")

def get_urifilename(uri):
    """ extract the uri path and return the last element """
    up=urlparse.urlparse(uri)
    return split(up[2],"/")[-1]

def get_parenturi(uri):
    """ return the parent of the given resource"""
    up=urlparse.urlparse(uri)
    np=joinfields(split(up[2],"/")[:-1],"/")
    return urlparse.urlunparse((up[0],up[1],np,up[3],up[4],up[5]))

### XML utilities

def make_xmlresponse(result):
    """ construct a response from a dict of uri:error_code elements """
    doc = minidom.getDOMImplementation().createDocument(None, "multistatus", None)
    doc.documentElement.setAttribute("xmlns:D","DAV:")
    doc.documentElement.tagName = "D:multistatus"

    for el,ec in result.items():
        re=doc.createElementNS("DAV:","response")
        hr=doc.createElementNS("DAV:","href")
        st=doc.createElementNS("DAV:","status")
        huri=doc.createTextNode(quote_uri(el))
        t=doc.createTextNode(gen_estring(ec))
        st.appendChild(t)
        hr.appendChild(huri)
        re.appendChild(hr)
        re.appendChild(st)
        doc.documentElement.appendChild(re)

    return doc.toxml(encoding="utf-8")

# taken from App.Common

weekday_abbr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
weekday_full = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday']
monthname    = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def rfc1123_date(ts=None):
    # Return an RFC 1123 format date string, required for
    # use in HTTP Date headers per the HTTP 1.1 spec.
    # 'Fri, 10 Nov 2000 16:21:09 GMT'
    if ts is None: ts=time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekday_abbr[wd],
                                                    day, monthname[month],
                                                    year,
                                                    hh, mm, ss)
def iso8601_date(ts=None):
    # Return an ISO 8601 formatted date string, required
    # for certain DAV properties.
    # '2000-11-10T16:21:09-08:00
    if ts is None: ts=time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))

def rfc850_date(ts=None):
    # Return an HTTP-date formatted date string.
    # 'Friday, 10-Nov-00 16:21:09 GMT'
    if ts is None: ts=time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d-%3s-%2s %02d:%02d:%02d GMT" % (
            weekday_full[wd],
            day, monthname[month],
            str(year)[2:],
            hh, mm, ss)

### If: header handling support.  IfParser returns a sequence of
### TagList objects in the order they were parsed which can then
### be used in WebDAV methods to decide whether an operation can
### proceed or to raise HTTP Error 412 (Precondition failed)
IfHdr = re.compile(
    r"(?P<resource><.+?>)?\s*\((?P<listitem>[^)]+)\)"
    )

ListItem = re.compile(
    r"(?P<not>not)?\s*(?P<listitem><[a-zA-Z]+:[^>]*>|\[.*?\])",
    re.I)

class TagList:
    def __init__(self):
        self.resource = None
        self.list = []
        self.NOTTED = 0

def IfParser(hdr):
    out = []
    i = 0
    while 1:
        m = IfHdr.search(hdr[i:])
        if not m: break

        i = i + m.end()
        tag = TagList()
        tag.resource = m.group('resource')
        if tag.resource:                # We need to delete < >
            tag.resource = tag.resource[1:-1]
        listitem = m.group('listitem')
        tag.NOTTED, tag.list = ListParser(listitem)
        out.append(tag)

    return out

def tokenFinder(token):
    # takes a string like '<opaquelocktoken:afsdfadfadf> and returns the token
    # part.
    if not token: return None           # An empty string was passed in
    if token[0] == '[': return None     # An Etag was passed in
    if token[0] == '<': token = token[1:-1]
    return token[token.find(':')+1:]

def ListParser(listitem):
    out = []
    NOTTED = 0
    i = 0
    while 1:
        m = ListItem.search(listitem[i:])
        if not m: break

        i = i + m.end()
        out.append(m.group('listitem'))
        if m.group('not'): NOTTED = 1

    return NOTTED, out
