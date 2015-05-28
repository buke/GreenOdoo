# definition for resourcetype
COLLECTION=1
OBJECT=None

# attributes for resources
DAV_PROPS=['creationdate', 'displayname', 'getcontentlanguage', 'getcontentlength', 'getcontenttype', 'getetag', 'getlastmodified', 'lockdiscovery', 'resourcetype', 'source', 'supportedlock']

# Request classes in propfind
RT_ALLPROP=1
RT_PROPNAME=2
RT_PROP=3

# server mode
DAV_VERSION_1 = {
        'version' : '1',
        'options' : 
        'GET, HEAD, COPY, MOVE, POST, PUT, PROPFIND, PROPPATCH, OPTIONS, MKCOL, DELETE, TRACE, REPORT'
}

DAV_VERSION_2 = {
        'version' : '1,2',
        'options' : 
        DAV_VERSION_1['options'] + ', LOCK, UNLOCK'
}
