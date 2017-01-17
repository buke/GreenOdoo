# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.

import weakref, re, os, sys
from ConfigParser import SafeConfigParser as ConfigParser,\
    NoSectionError, NoOptionError
from urlparse import urlparse

from ZSI import TC
from ZSI.client import _Binding
from ZSI.generate import commands,containers
from ZSI.schema import GED, GTD

import wstools
#from ZSI.wstools.Utility import SplitQName
#from ZSI.wstools.Namespaces import WSDL


#url_to_mod = re.compile(r'<([^ \t\n\r\f\v:]+:)?include\s+location\s*=\s*"(\S+)"')
def _urn_to_module(urn): return '%s_types' %re.sub(_urn_to_module.regex, '_', urn)
_urn_to_module.regex = re.compile(r'[\W]')
    

class ServiceProxy:
    """A ServiceProxy provides a convenient way to call a remote web
       service that is described with WSDL. The proxy exposes methods
       that reflect the methods of the remote web service."""

    def __init__(self, wsdl, url=None, service=None, port=None, tracefile=None,
                 nsdict=None, transport=None, transdict=None, 
                 cachedir='.service_proxy_dir', asdict=True):
        """
        Parameters:
           wsdl -- URL of WSDL.
           url -- override WSDL SOAP address location
           service -- service name or index
           port -- port name or index
           tracefile -- 
           nsdict -- key prefix to namespace mappings for serialization
              in SOAP Envelope.
           transport -- override default transports.
           transdict -- arguments to pass into HTTPConnection constructor.
           cachedir -- where to store generated files
           asdict -- use dicts, else use generated pyclass
        """
        self._asdict = asdict
        
        # client._Binding
        self._tracefile = tracefile
        self._nsdict = nsdict or {}
        self._transdict = transdict 
        self._transport = transport
        self._url = url
        
        # WSDL
        self._wsdl = wstools.WSDLTools.WSDLReader().loadFromURL(wsdl)
        self._service = self._wsdl.services[service or 0]
        self.__doc__ = self._service.documentation
        self._port = self._service.ports[port or 0]
        self._name = self._service.name
        self._methods = {}
        
        # Set up rpc methods for service/port
        port = self._port
        binding = port.getBinding()
        portType = binding.getPortType()
        for port in self._service.ports:
            for item in port.getPortType().operations:
                callinfo = wstools.WSDLTools.callInfoFromWSDL(port, item.name)
                method = MethodProxy(self, callinfo)
                setattr(self, item.name, method)
                self._methods.setdefault(item.name, []).append(method)
       
        # wsdl2py: deal with XML Schema
        if not os.path.isdir(cachedir): os.mkdir(cachedir)
    
        file = os.path.join(cachedir, '.cache')
        section = 'TYPES'
        cp = ConfigParser()
        try:
            cp.readfp(open(file, 'r'))
        except IOError:
            del cp;  cp = None
            
        option = wsdl.replace(':', '-') # colons seem to screw up option
        if (cp is not None and cp.has_section(section) and 
            cp.has_option(section, option)):
            types = cp.get(section, option)
        else:
            # dont do anything to anames
            containers.ContainerBase.func_aname = lambda instnc,n: str(n)
            #client,types = commands.wsdl2py(['-u', wsdl,'-o', cachedir, '-t', "%s_types.py" %])
            types = _urn_to_module(wsdl)
            commands.wsdl2py(['-u', wsdl,'-o', cachedir, '-t', types])
            if cp is None: cp = ConfigParser()
            if not cp.has_section(section): cp.add_section(section)
            cp.set(section, option, types)
            cp.write(open(file, 'w'))
            
        if os.path.abspath(cachedir) not in sys.path:
            sys.path.append(os.path.abspath(cachedir))

        self._mod = __import__(types)
        
    def _call(self, name, *args, **kwargs):
        """Call the named remote web service method."""
        if len(args) and len(kwargs):
            raise TypeError(
                'Use positional or keyword argument only.'
                )

        callinfo = getattr(self, name).callinfo

        # go through the list of defined methods, and look for the one with
        # the same number of arguments as what was passed.  this is a weak
        # check that should probably be improved in the future to check the
        # types of the arguments to allow for polymorphism
        for method in self._methods[name]:
            if len(method.callinfo.inparams) == len(kwargs):
                callinfo = method.callinfo

        binding = _Binding(tracefile=self._tracefile,
                          url=self._url or callinfo.location, 
                          nsdict=self._nsdict, 
                          soapaction=callinfo.soapAction)


        if len(kwargs): args = kwargs

        kw = dict(unique=True)
        if callinfo.use == 'encoded':
            kw['unique'] = False

        if callinfo.style == 'rpc':
            request = TC.Struct(None, ofwhat=[], 
                             pname=(callinfo.namespace, name), **kw)
            
            response = TC.Struct(None, ofwhat=[], 
                             pname=(callinfo.namespace, name+"Response"), **kw)
            
            if len(callinfo.getInParameters()) != len(args):
                raise RuntimeError('expecting "%s" parts, got %s' %(
                       str(callinfo.getInParameters(), str(args))))
            
            for msg,pms in ((request,callinfo.getInParameters()), 
                            (response,callinfo.getOutParameters())):
                msg.ofwhat = []
                for part in pms:
                    klass = GTD(*part.type)
                    if klass is None:
                        if part.type:
                            klass = filter(lambda gt: part.type==gt.type,TC.TYPES)
                            if len(klass) == 0:
                                klass = filter(lambda gt: part.type[1]==gt.type[1],TC.TYPES)
                                if not len(klass):klass = [TC.Any]
                            if len(klass) > 1: #Enumerations, XMLString, etc
                                klass = filter(lambda i: i.__dict__.has_key('type'), klass)
                            klass = klass[0]
                        else:
                            klass = TC.Any
                
                    msg.ofwhat.append(klass(part.name))
                    
                msg.ofwhat = tuple(msg.ofwhat)
            if not args: args = {}
        else:
            # Grab <part element> attribute
            ipart,opart = callinfo.getInParameters(),callinfo.getOutParameters()
            if ( len(ipart) != 1 or not ipart[0].element_type or 
                ipart[0].type is None ):
                raise RuntimeError, 'Bad Input Message "%s"' %callinfo.name
    
            if ( len(opart) not in (0,1) or not opart[0].element_type or 
                opart[0].type is None ):
                raise RuntimeError, 'Bad Output Message "%s"' %callinfo.name
            
            if ( len(args) != 1 ):
                raise RuntimeError, 'Message has only one part'
            
            ipart = ipart[0]
            request,response = GED(*ipart.type),None
            if opart: response = GED(*opart[0].type)

        if self._asdict: self._nullpyclass(request)
        binding.Send(None, None, args,
                     requesttypecode=request,
                     encodingStyle=callinfo.encodingStyle)
        
        if response is None: 
            return None
        
        if self._asdict: self._nullpyclass(response)
        return binding.Receive(replytype=response,
                     encodingStyle=callinfo.encodingStyle)
        
    def _nullpyclass(cls, typecode):
        typecode.pyclass = None
        if not hasattr(typecode, 'ofwhat'): return
        if type(typecode.ofwhat) not in (list,tuple): #Array
            cls._nullpyclass(typecode.ofwhat)
        else: #Struct/ComplexType
            for i in typecode.ofwhat: cls._nullpyclass(i)    
    _nullpyclass = classmethod(_nullpyclass)
        
        
#
#
#    def _getTypeCodes(self, callinfo):
#        """Returns typecodes representing input and output messages, if request and/or
#           response fails to be generated return None for either or both.
#           
#           callinfo --  WSDLTools.SOAPCallInfo instance describing an operation.
#        """
#        prefix = None
#        self._resetPrefixDict()
#        if callinfo.use == 'encoded':
#            prefix = self._getPrefix(callinfo.namespace)
#        try:
#            requestTC = self._getTypeCode(parameters=callinfo.getInParameters(), literal=(callinfo.use=='literal'))
#        except EvaluateException, ex:
#            print "DEBUG: Request Failed to generate --", ex
#            requestTC = None
#
#        self._resetPrefixDict()
#        try:
#            replyTC = self._getTypeCode(parameters=callinfo.getOutParameters(), literal=(callinfo.use=='literal'))
#        except EvaluateException, ex:
#            print "DEBUG: Response Failed to generate --", ex
#            replyTC = None
#        
#        request = response = None
#        if callinfo.style == 'rpc':
#            if requestTC: request = TC.Struct(pyclass=None, ofwhat=requestTC, pname=callinfo.methodName)
#            if replyTC: response = TC.Struct(pyclass=None, ofwhat=replyTC, pname='%sResponse' %callinfo.methodName)
#        else:
#            if requestTC: request = requestTC[0]
#            if replyTC: response = replyTC[0]
#
#        #THIS IS FOR RPC/ENCODED, DOC/ENCODED Wrapper
#        if request and prefix and callinfo.use == 'encoded':
#            request.oname = '%(prefix)s:%(name)s xmlns:%(prefix)s="%(namespaceURI)s"' \
#                %{'prefix':prefix, 'name':request.aname, 'namespaceURI':callinfo.namespace}
#
#        return request, response
#
#    def _getTypeCode(self, parameters, literal=False):
#        """Returns typecodes representing a parameter set
#           parameters -- list of WSDLTools.ParameterInfo instances representing
#              the parts of a WSDL Message.
#        """
#        ofwhat = []
#        for part in parameters:
#            namespaceURI,localName = part.type
#
#            if part.element_type:
#                #global element
#                element = self._wsdl.types[namespaceURI].elements[localName]
#                tc = self._getElement(element, literal=literal, local=False, namespaceURI=namespaceURI)
#            else:
#                #local element
#                name = part.name
#                typeClass = self._getTypeClass(namespaceURI, localName)
#                if not typeClass:
#                    tp = self._wsdl.types[namespaceURI].types[localName]
#                    tc = self._getType(tp, name, literal, local=True, namespaceURI=namespaceURI)
#                else:
#                    tc = typeClass(name)
#            ofwhat.append(tc)
#        return ofwhat
#
#    def _globalElement(self, typeCode, namespaceURI, literal):
#        """namespaces typecodes representing global elements with 
#             literal encoding.
#           typeCode -- typecode representing an element.
#           namespaceURI -- namespace 
#           literal -- True/False
#        """
#        if literal:
#            typeCode.oname = '%(prefix)s:%(name)s xmlns:%(prefix)s="%(namespaceURI)s"' \
#                %{'prefix':self._getPrefix(namespaceURI), 'name':typeCode.oname, 'namespaceURI':namespaceURI}
#
#    def _getPrefix(self, namespaceURI):
#        """Retrieves a prefix/namespace mapping.
#           namespaceURI -- namespace 
#        """
#        prefixDict = self._getPrefixDict()
#        if prefixDict.has_key(namespaceURI):
#            prefix = prefixDict[namespaceURI]
#        else:
#            prefix = 'ns1'
#            while prefix in prefixDict.values():
#                prefix = 'ns%d' %int(prefix[-1]) + 1
#            prefixDict[namespaceURI] = prefix
#        return prefix
#
#    def _getPrefixDict(self):
#        """Used to hide the actual prefix dictionary.
#        """
#        if not hasattr(self, '_prefixDict'):
#            self.__prefixDict = {}
#        return self.__prefixDict
#
#    def _resetPrefixDict(self):
#        """Clears the prefix dictionary, this needs to be done 
#           before creating a new typecode for a message 
#           (ie. before, and after creating a new message typecode)
#        """
#        self._getPrefixDict().clear()
#
#    def _getElement(self, element, literal=False, local=False, namespaceURI=None):
#        """Returns a typecode instance representing the passed in element.
#           element -- XMLSchema.ElementDeclaration instance
#           literal -- literal encoding?
#           local -- is locally defined?
#           namespaceURI -- namespace
#        """
#        if not element.isElement():
#            raise TypeError, 'Expecting an ElementDeclaration'
#
#        tc = None
#        elementName = element.getAttribute('name')
#        tp = element.getTypeDefinition('type')
#
#        typeObj = None
#        if not (tp or element.content):
#            nsuriType,localName = element.getAttribute('type')
#            typeClass = self._getTypeClass(nsuriType,localName)
#            
#            typeObj = typeClass(elementName)
#        elif not tp:
#            tp = element.content
#
#        if not typeObj:
#            typeObj = self._getType(tp, elementName, literal, local, namespaceURI)
#
#        minOccurs = int(element.getAttribute('minOccurs'))
#        typeObj.optional = not minOccurs
#        typeObj.minOccurs = minOccurs
#
#        maxOccurs = element.getAttribute('maxOccurs')
#        typeObj.repeatable = (maxOccurs == 'unbounded') or (int(maxOccurs) > 1)
#
#        return typeObj
#
#    def _getType(self, tp, name, literal, local, namespaceURI):
#        """Returns a typecode instance representing the passed in type and name.
#           tp -- XMLSchema.TypeDefinition instance
#           name -- element name
#           literal -- literal encoding?
#           local -- is locally defined?
#           namespaceURI -- namespace
#        """
#        ofwhat = []
#        if not (tp.isDefinition() and tp.isComplex()):
#            raise EvaluateException, 'only supporting complexType definition'
#        elif tp.content.isComplex():
#            if hasattr(tp.content, 'derivation') and tp.content.derivation.isRestriction():
#                derived = tp.content.derivation
#                typeClass = self._getTypeClass(*derived.getAttribute('base'))
#                if typeClass == TC.Array:
#                    attrs = derived.attr_content[0].attributes[WSDL.BASE]
#                    prefix, localName = SplitQName(attrs['arrayType'])
#                    nsuri = derived.attr_content[0].getXMLNS(prefix=prefix)
#                    localName = localName.split('[')[0]
#                    simpleTypeClass = self._getTypeClass(namespaceURI=nsuri, localName=localName)
#                    if simpleTypeClass:
#                        ofwhat = simpleTypeClass()
#                    else:
#                        tp = self._wsdl.types[nsuri].types[localName]
#                        ofwhat = self._getType(tp=tp, name=None, literal=literal, local=True, namespaceURI=nsuri)
#                else:
#                    raise EvaluateException, 'only support soapenc:Array restrictions'
#                return typeClass(atype=name, ofwhat=ofwhat, pname=name, childNames='item')
#            else:
#                raise EvaluateException, 'complexContent only supported for soapenc:Array derivations'
#        elif tp.content.isModelGroup():
#            modelGroup = tp.content
#            for item in modelGroup.content:
#                ofwhat.append(self._getElement(item, literal=literal, local=True))
#
#            tc = TC.Struct(pyclass=None, ofwhat=ofwhat, pname=name)
#            if not local:
#                self._globalElement(tc, namespaceURI=namespaceURI, literal=literal)
#            return tc
#
#        raise EvaluateException, 'only supporting complexType w/ model group, or soapenc:Array restriction'
#   
#    def _getTypeClass(self, namespaceURI, localName):
#        """Returns a typecode class representing the type we are looking for.
#           localName -- name of the type we are looking for.
#           namespaceURI -- defining XMLSchema targetNamespace.
#        """
#        bti = BaseTypeInterpreter()
#        simpleTypeClass = bti.get_typeclass(localName, namespaceURI)
#        return simpleTypeClass


class MethodProxy:
    """ """
    def __init__(self, parent, callinfo):
        self.__name__ = callinfo.methodName
        self.__doc__ = callinfo.documentation
        self.callinfo = callinfo
        self.parent = weakref.ref(parent)

    def __call__(self, *args, **kwargs):
        return self.parent()._call(self.__name__, *args, **kwargs)
