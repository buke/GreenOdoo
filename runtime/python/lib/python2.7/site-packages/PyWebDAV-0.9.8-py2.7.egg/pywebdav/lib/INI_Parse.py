from ConfigParser import SafeConfigParser

class Configuration:
    def __init__(self, fileName):
        cp = SafeConfigParser()
        cp.read(fileName)
        self.__parser = cp
        self.fileName = fileName

    def __getattr__(self, name):
        if name in self.__parser.sections():
            return Section(name, self.__parser)
        else:
            return None

    def __str__(self):
        p = self.__parser
        result = []
        result.append('<Configuration from %s>' % self.fileName)
        for s in p.sections():
            result.append('[%s]' % s)
            for o in p.options(s):
                result.append('%s=%s' % (o, p.get(s, o)))
        return '\n'.join(result)

class Section:
    def __init__(self, name, parser):
        self.name = name
        self.__parser = parser

    def __getattr__(self, name):
        return self.__parser.get(self.name, name)

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        return self.__parser.items(self.name)

    def getboolean(self, name):
        return self.__parser.getboolean(self.name, name)

    def __contains__(self, name):
        return self.__parser.has_option(self.name, name)

    def get(self, name, default):
        if name in self:
            return self.__getattr__(name)
        else:
            return default

    def set(self, name, value):
        self.__parser.set(self.name, name, str(value))

# Test
if __name__ == '__main__':
    c = Configuration('Importador.ini')
    print c.Origem.host, c.Origem.port
