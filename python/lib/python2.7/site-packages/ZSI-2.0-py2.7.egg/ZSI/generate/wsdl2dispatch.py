#!/usr/bin/env python
from cStringIO import StringIO
import ZSI, string, sys, getopt, urlparse, types, warnings
from ZSI.wstools import WSDLTools
from ZSI.generate.wsdl2python import WriteServiceModule, MessageTypecodeContainer
from ZSI.ServiceContainer import ServiceSOAPBinding, SimpleWSResource, WSAResource
from ZSI.generate.utility import TextProtect, GetModuleBaseNameFromWSDL, NCName_to_ClassName, GetPartsSubNames, TextProtectAttributeName
from ZSI.generate import WsdlGeneratorError, Wsdl2PythonError
from ZSI.generate.wsdl2python import SchemaDescription


# Split last token
rsplit = lambda x,sep,: (x[:x.rfind(sep)], x[x.rfind(sep)+1:],)
if sys.version_info[0:2] == (2, 4, 0, 'final', 0)[0:2]:
    rsplit = lambda x,sep,: x.rsplit(sep, 1)

class SOAPService:
    def __init__(self, service):
        self.classdef = StringIO()
        self.initdef  = StringIO()
        self.location = ''
        self.methods  = []

    def newMethod(self):
        '''name -- operation name
        '''
        self.methods.append(StringIO())
        return self.methods[-1]

class ServiceModuleWriter:
    '''Creates a skeleton for a SOAP service instance.
    '''
    indent = ' '*4
    server_module_suffix = '_services_server'
    func_aname = TextProtectAttributeName
    func_aname = staticmethod(func_aname)
    separate_messages = False # Whether to write message definitions into a separate file.

    def __init__(self, base=ServiceSOAPBinding, prefix='soap', service_class=SOAPService, do_extended=False):
        '''
        parameters:
            base -- either a class definition, or a str representing a qualified class name.
            prefix -- method prefix.
        '''
        self.wsdl = None
        self.base_class = base
        self.method_prefix = prefix
        self._service_class = SOAPService

        self.header  = None
        self.imports  = None
        self._services = None
        self.client_module_path = None
        self.client_module_name = None
        self.messages_module_name = None
        self.do_extended = do_extended

    def reset(self):
        self.header  = StringIO()
        self.imports  = StringIO()
        self._services = {}

    def _getBaseClassName(self):
        '''return base class name, do not override.
        '''
        if type(self.base_class) is types.ClassType:
            return self.base_class.__name__
        return rsplit(self.base_class, '.')[-1]

    def _getBaseClassModule(self):
        '''return base class module, do not override.
        '''
        if type(self.base_class) is types.ClassType:
            return self.base_class.__module__
        if self.base_class.find('.') >= 0:
            return rsplit(self.base_class, '.')[0]
        return None

    def getIndent(self, level=1):
        '''return indent.
        '''
        assert 0 < level < 10, 'bad indent level %d' %level
        return self.indent*level

    def getMethodName(self, method):
        '''return method name.
        '''
        return '%s_%s' %(self.method_prefix, TextProtect(method))

    def getClassName(self, name):
        '''return class name.
        '''
        return NCName_to_ClassName(name)

    def setClientModuleName(self, name):
        self.client_module_name = name

    def getClientModuleName(self):
        '''return module name.
        '''
        assert self.wsdl is not None, 'initialize, call fromWSDL'
        if self.client_module_name is not None:
            return self.client_module_name

        wsm = WriteServiceModule(self.wsdl, do_extended=self.do_extended)
        return wsm.getClientModuleName()

    def getMessagesModuleName(self):
        '''return module name.
        '''
        assert self.wsdl is not None, 'initialize, call fromWSDL'
        if self.messages_module_name is not None:
            return self.messages_module_name

        wsm = WriteServiceModule(self.wsdl, do_extended=self.do_extended)
        return wsm.getMessagesModuleName()
    
    def getServiceModuleName(self):
        '''return module name.
        '''
        name = GetModuleBaseNameFromWSDL(self.wsdl)
        if not name:
            raise WsdlGeneratorError, 'could not determine a service name'
        
        if self.server_module_suffix is None:
            return name
        return '%s%s' %(name, self.server_module_suffix)

    def getClientModulePath(self):
        return self.client_module_path

    def setClientModulePath(self, path):
        '''setup module path to where client module before calling fromWSDL.
        '''
        self.client_module_path = path

    def setUpClassDef(self, service):
        '''set class definition and class variables.
        service -- ServiceDescription instance
        '''
        assert isinstance(service, WSDLTools.Service) is True,\
            'expecting WSDLTools.Service instance.'

        s = self._services[service.name].classdef
        print >>s, 'class %s(%s):' %(self.getClassName(service.name), self._getBaseClassName())
        print >>s, '%ssoapAction = {}' % self.getIndent(level=1)
        print >>s, '%sroot = {}' % self.getIndent(level=1)
	print >>s, "%s_wsdl = \"\"\"%s\"\"\"" % (self.getIndent(level=1), self.raw_wsdl)

    def setUpImports(self):
        '''set import statements
        '''
        path = self.getClientModulePath()
        i = self.imports
        if path is None:
            if self.separate_messages:
                print >>i, 'from %s import *' %self.getMessagesModuleName()
            else:
                print >>i, 'from %s import *' %self.getClientModuleName()
        else:
            if self.separate_messages:
                print >>i, 'from %s.%s import *' %(path, self.getMessagesModuleName())
            else:
                print >>i, 'from %s.%s import *' %(path, self.getClientModuleName())

        mod = self._getBaseClassModule()
        name = self._getBaseClassName()
        if mod is None:
            print >>i, 'import %s' %name
        else:
            print >>i, 'from %s import %s' %(mod, name)

    def setUpInitDef(self, service):
        '''set __init__ function
        '''
        assert isinstance(service, WSDLTools.Service), 'expecting WSDLTools.Service instance.'
        sd = self._services[service.name]
        d = sd.initdef
 
        if sd.location is not None:
            scheme,netloc,path,params,query,fragment = urlparse.urlparse(sd.location)
            print >>d, '%sdef __init__(self, post=\'%s\', **kw):' %(self.getIndent(level=1), path)
        else:
            print >>d, '%sdef __init__(self, post, **kw):' %self.getIndent(level=1)

        print >>d, '%s%s.__init__(self, post)' %(self.getIndent(level=2),self._getBaseClassName())


    def mangle(self, name):
        return TextProtect(name)

    def getAttributeName(self, name):
        return self.func_aname(name)

    def setUpMethods(self, port):
        '''set up all methods representing the port operations.
        Parameters:
            port -- Port that defines the operations.
        '''
        assert isinstance(port, WSDLTools.Port), \
            'expecting WSDLTools.Port not: ' %type(port)

        sd = self._services.get(port.getService().name)
        assert sd is not None, 'failed to initialize.'

        binding = port.getBinding()
        portType = port.getPortType()
        action_in = ''
        for bop in binding.operations:
            try:
                op = portType.operations[bop.name]
            except KeyError, ex:
                raise WsdlGeneratorError,\
                    'Port(%s) PortType(%s) missing operation(%s) defined in Binding(%s)' \
                    %(port.name,portType.name,bop.name,binding.name)

            for ext in bop.extensions:
                 if isinstance(ext, WSDLTools.SoapOperationBinding):
                     action_in = ext.soapAction
                     break
            else:
                warnings.warn('Port(%s) operation(%s) defined in Binding(%s) missing soapAction' \
                    %(port.name,op.name,binding.name)
                )

            msgin = op.getInputMessage()
            msgin_name = TextProtect(msgin.name)
            method_name = self.getMethodName(op.name)

            m = sd.newMethod()
            print >>m, '%sdef %s(self, ps):' %(self.getIndent(level=1), method_name)
            if msgin is not None:
                print >>m, '%sself.request = ps.Parse(%s.typecode)' %(self.getIndent(level=2), msgin_name)
            else:
                print >>m, '%s# NO input' %self.getIndent(level=2)

            msgout = op.getOutputMessage()

            if self.do_extended:
                input_args = msgin.parts.values()
                iargs = ["%s" % x.name for x in input_args]
                if msgout is not None:
                    output_args = msgout.parts.values()
                else:
                    output_args = []
                oargs = ["%s" % x.name for x in output_args]
                if output_args:
                    if len(output_args) > 1:
                        print "Message has more than one return value (Bad Design)."
                        output_args = "(%s)" % output_args
                else:
                    output_args = ""
                # Get arg list
                iSubNames = GetPartsSubNames(msgin.parts.values(), self.wsdl)
                for i in range( len(iargs) ):  # should only be one part to messages here anyway
                    argSubNames = iSubNames[i]
                    if len(argSubNames) > 0:
                        subNamesStr = "self.request." + ", self.request.".join(map(self.getAttributeName, argSubNames))
                        if len(argSubNames) > 1:
                            subNamesStr = "(" + subNamesStr + ")"
                        print >>m, "%s%s = %s" % (self.getIndent(level=2), iargs[i], subNamesStr)
                        
                print >>m, "\n%s# If we have an implementation object use it" % (self.getIndent(level=2))
                print >>m, "%sif hasattr(self,'impl'):" % (self.getIndent(level=2))

                iargsStrList = []  
                for arg in iargs:
                    argSubNames = iSubNames[i]
                    if len(argSubNames) > 0:
                        if len(argSubNames) > 1:
                            for i in range(len(argSubNames)):
                                iargsStrList.append( arg + "[%i]" % i )
                        else:
                            iargsStrList.append( arg  )
                iargsStr =  ",".join(iargsStrList)
                oargsStr = ", ".join(oargs) 
                if len(oargsStr) > 0:
                    oargsStr += " = "
                print >>m, "%s%sself.impl.%s(%s)" % (self.getIndent(level=3), oargsStr, op.name, iargsStr)
        
            if msgout is not None:
                msgout_name = TextProtect(msgout.name)
                if self.do_extended:
                    print >>m, '\n%sresult = %s()' %(self.getIndent(level=2), msgout_name)
                    oSubNames = GetPartsSubNames(msgout.parts.values(), self.wsdl)
                    if (len(oSubNames) > 0) and (len(oSubNames[0]) > 0):
                        print >>m, "%s# If we have an implementation object, copy the result " % (self.getIndent(level=2))
                        print >>m, "%sif hasattr(self,'impl'):" % (self.getIndent(level=2))
                        # copy result's members
                        for i in range( len(oargs) ):  # should only be one part messages here anyway
                            oargSubNames = oSubNames[i]
                            if len(oargSubNames) > 1:
                                print >>m, '%s# Should have a tuple of %i args' %(self.getIndent(level=3), len(oargSubNames))
                                for j in range(len(oargSubNames)):
                                    oargSubName = oargSubNames[j]
                                    print >>m, '%sresult.%s = %s[%i]' %(self.getIndent(level=3), self.getAttributeName(oargSubName), oargs[i], j)
                            elif len(oargSubNames) == 1:
                                oargSubName = oargSubNames[0]
                                print >>m, '%sresult.%s = %s' %(self.getIndent(level=3), self.getAttributeName(oargSubName), oargs[i])
                            else:
                                raise Exception("The subnames within message " + msgout_name + "'s part were not found.  Message is the output of operation " + op.name)
                    print >>m, '%sreturn result' %(self.getIndent(level=2))
                else:
                    print >>m, '%sreturn %s()' %(self.getIndent(level=2), msgout_name)
            else:
                print >>m, '%s# NO output' % self.getIndent(level=2)
                print >>m, '%sreturn None' % self.getIndent(level=2)

            print >>m, ''
            print >>m, '%ssoapAction[\'%s\'] = \'%s\'' %(self.getIndent(level=1), action_in, method_name)
            print >>m, '%sroot[(%s.typecode.nspname,%s.typecode.pname)] = \'%s\'' \
                     %(self.getIndent(level=1), msgin_name, msgin_name, method_name)

        return

    def setUpHeader(self):
        print >>self.header, '##################################################'
        print >>self.header, '# %s.py' %self.getServiceModuleName()
        print >>self.header, '#      Generated by %s' %(self.__class__)
        print >>self.header, '#'
        print >>self.header, '##################################################'

    def write(self, fd=sys.stdout):
        '''write out to file descriptor, 
        should not need to override.
        '''
        print >>fd, self.header.getvalue()
        print >>fd, self.imports.getvalue()
        for k,v in self._services.items():
            print >>fd, v.classdef.getvalue()
            print >>fd, v.initdef.getvalue()
            for s in v.methods:
                print >>fd, s.getvalue()

    def fromWSDL(self, wsdl):
        '''setup the service description from WSDL,
        should not need to override.
        '''
        assert isinstance(wsdl, WSDLTools.WSDL), 'expecting WSDL instance'

        if len(wsdl.services) == 0:
            raise WsdlGeneratorError, 'No service defined'
      
        self.reset() 
        self.wsdl = wsdl
	self.raw_wsdl = wsdl.document.toxml().replace("\"", "\\\"")
        self.setUpHeader()
        self.setUpImports()
        for service in wsdl.services:
            sd = self._service_class(service.name)
            self._services[service.name] = sd

            for port in service.ports:
                for e in port.extensions:
                    if isinstance(e, WSDLTools.SoapAddressBinding):
                        sd.location = e.location

                self.setUpMethods(port)

            self.setUpClassDef(service)
            self.setUpInitDef(service)


class WSAServiceModuleWriter(ServiceModuleWriter):
    '''Creates a skeleton for a WS-Address service instance.
    '''
    def __init__(self, base=WSAResource, prefix='wsa', service_class=SOAPService, strict=True):
        '''
        Parameters:
            strict -- check that soapAction and input ws-action do not collide.
        '''
        ServiceModuleWriter.__init__(self, base, prefix, service_class)
        self.strict = strict

    def createMethodBody(msgInName, msgOutName, **kw):
        '''return a tuple of strings containing the body of a method.
        msgInName -- None or a str
        msgOutName --  None or a str
        '''
        body = []
        if msgInName is not None:
            body.append('self.request = ps.Parse(%s.typecode)' %msgInName)
            
        if msgOutName is not None:
            body.append('return %s()' %msgOutName)
        else: 
            body.append('return None')
            
        return tuple(body)
    createMethodBody = staticmethod(createMethodBody)

    def setUpClassDef(self, service):
        '''use soapAction dict for WS-Action input, setup wsAction
        dict for grabbing WS-Action output values.
        '''
        assert isinstance(service, WSDLTools.Service), 'expecting WSDLTools.Service instance'

        s = self._services[service.name].classdef
        print >>s, 'class %s(%s):' %(self.getClassName(service.name), self._getBaseClassName())
        print >>s, '%ssoapAction = {}' % self.getIndent(level=1)
        print >>s, '%swsAction = {}' % self.getIndent(level=1)
        print >>s, '%sroot = {}' % self.getIndent(level=1)

    def setUpMethods(self, port):
        '''set up all methods representing the port operations.
        Parameters:
            port -- Port that defines the operations.
        '''
        assert isinstance(port, WSDLTools.Port), \
            'expecting WSDLTools.Port not: ' %type(port)

        binding = port.getBinding()
        portType = port.getPortType()
        service = port.getService()
        s = self._services[service.name]
        for bop in binding.operations:
            try:
                op = portType.operations[bop.name]
            except KeyError, ex:
                raise WsdlGeneratorError,\
                    'Port(%s) PortType(%s) missing operation(%s) defined in Binding(%s)' \
                    %(port.name, portType.name, op.name, binding.name)

            soap_action = wsaction_in = wsaction_out = None
            if op.input is not None:
                wsaction_in = op.getInputAction()
            if op.output is not None:
                wsaction_out = op.getOutputAction()

            for ext in bop.extensions:
                if isinstance(ext, WSDLTools.SoapOperationBinding) is False: continue
                soap_action = ext.soapAction
                if not soap_action: break
                if wsaction_in is None: break
                if wsaction_in == soap_action: break
                if self.strict is False:
                    warnings.warn(\
                        'Port(%s) operation(%s) in Binding(%s) soapAction(%s) != WS-Action(%s)' \
                         %(port.name, op.name, binding.name, soap_action, wsaction_in),
                    )
                    break
                raise WsdlGeneratorError,\
                    'Port(%s) operation(%s) in Binding(%s) soapAction(%s) MUST match WS-Action(%s)' \
                     %(port.name, op.name, binding.name, soap_action, wsaction_in)

            method_name = self.getMethodName(op.name)

            m = s.newMethod()
            print >>m, '%sdef %s(self, ps, address):' %(self.getIndent(level=1), method_name)
            
            msgin_name = msgout_name = None
            msgin,msgout = op.getInputMessage(),op.getOutputMessage()
            if msgin is not None: 
                msgin_name = TextProtect(msgin.name)
            if msgout is not None: 
                msgout_name = TextProtect(msgout.name)
        
            indent = self.getIndent(level=2)
            for l in self.createMethodBody(msgin_name, msgout_name):
                print >>m, indent + l

            print >>m, ''
            print >>m, '%ssoapAction[\'%s\'] = \'%s\'' %(self.getIndent(level=1), wsaction_in, method_name)
            print >>m, '%swsAction[\'%s\'] = \'%s\'' %(self.getIndent(level=1), method_name, wsaction_out)
            print >>m, '%sroot[(%s.typecode.nspname,%s.typecode.pname)] = \'%s\'' \
                     %(self.getIndent(level=1), msgin_name, msgin_name, method_name)
 

class DelAuthServiceModuleWriter(ServiceModuleWriter):
    ''' Includes the generation of lines to call an authorization method on the server side
        if an authorization function has been defined.
    '''
    def __init__(self, base=ServiceSOAPBinding, prefix='soap', service_class=SOAPService, do_extended=False):
        ServiceModuleWriter.__init__(self, base=base, prefix=prefix, service_class=service_class, do_extended=do_extended)

    def fromWSDL(self, wsdl):
        ServiceModuleWriter.fromWSDL(self, wsdl)
        for service in wsdl.services:
            self.setUpAuthDef(service)

    def setUpInitDef(self, service):
        ServiceModuleWriter.setUpInitDef(self, service)
        sd = self._services[service.name]
        d = sd.initdef
        print >>d,  '%sif kw.has_key(\'impl\'):' % self.getIndent(level=2)
        print >>d, '%sself.impl = kw[\'impl\']' % self.getIndent(level=3)

        print >>d, '%sself.auth_method_name = None' % self.getIndent(level=2)
        print >>d, '%sif kw.has_key(\'auth_method_name\'):' % self.getIndent(level=2)
        print >>d, '%sself.auth_method_name = kw[\'auth_method_name\']' % self.getIndent(level=3)

    def setUpAuthDef(self, service):
        '''set __auth__ function
        '''
        sd = self._services[service.name]
        e = sd.initdef
        print >>e, "%sdef authorize(self, auth_info, post, action):" % self.getIndent(level=1)
        print >>e, "%sif self.auth_method_name and hasattr(self.impl, self.auth_method_name):" % self.getIndent(level=2)
        print >>e, "%sreturn getattr(self.impl, self.auth_method_name)(auth_info, post, action)" % self.getIndent(level=3)
        print >>e, "%selse:" % self.getIndent(level=2)
        print >>e, "%sreturn 1" % self.getIndent(level=3)

class DelAuthWSAServiceModuleWriter(WSAServiceModuleWriter):
    def __init__(self, base=SimpleWSResource, prefix='wsa', service_class=SOAPService, strict=True):
        WSAServiceModuleWriter.__init__(self, base=base, prefix=prefix, service_class=service_class, strict=strict)

    def fromWSDL(self, wsdl):
        WSAServiceModuleWriter.fromWSDL(self, wsdl)
        for service in wsdl.services:
            self.setUpAuthDef(service)

    def setUpInitDef(self, service):
        WSAServiceModuleWriter.setUpInitDef(self, service)
        sd = self._services[service.name]
        d = sd.initdef
        print >>d,  '%sif kw.has_key(\'impl\'):' % self.getIndent(level=2)
        print >>d, '%sself.impl = kw[\'impl\']' % self.getIndent(level=3)

        print >>d, '%sif kw.has_key(\'auth_method_name\'):' % self.getIndent(level=2)
        print >>d, '%sself.auth_method_name = kw[\'auth_method_name\']' % self.getIndent(level=3)

    def setUpAuthDef(self, service):
        '''set __auth__ function
        '''
        sd = self._services[service.name]
        e = sd.initdef
        print >>e, "%sdef authorize(self, auth_info, post, action):" % self.getIndent(level=1)
        print >>e, "%sif self.auth_method_name and hasattr(self.impl, self.auth_method_name):" % self.getIndent(level=2)
        print >>e, "%sreturn getattr(self.impl, self.auth_method_name)(auth_info, post, action)" % self.getIndent(level=3)
        print >>e, "%selse:" % self.getIndent(level=2)
        print >>e, "%sreturn 1" % self.getIndent(level=3)

