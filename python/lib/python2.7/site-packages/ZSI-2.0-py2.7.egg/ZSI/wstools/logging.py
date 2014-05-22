# Copyright (c) 2003, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of
# any required approvals from the U.S. Dept. of Energy).  All rights
# reserved. 
#
"""Logging"""
ident = "$Id: logging.py 1204 2006-05-03 00:13:47Z boverhof $"
import sys

WARN = 1
DEBUG = 2


class ILogger:
    '''Logger interface, by default this class
    will be used and logging calls are no-ops.
    '''
    level = 0
    def __init__(self, msg):
        return
    def warning(self, *args):
        return
    def debug(self, *args):
        return
    def error(self, *args):
        return
    def setLevel(cls, level):
        cls.level = level
    setLevel = classmethod(setLevel)
    
    debugOn = lambda self: self.level >= DEBUG
    warnOn = lambda self: self.level >= WARN
    

class BasicLogger(ILogger):
    last = ''
    
    def __init__(self, msg, out=sys.stdout):
        self.msg, self.out = msg, out

    def warning(self, msg, *args):
        if self.warnOn() is False: return
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %BasicLogger.WARN,
        print >>self, msg %args
    WARN = '[WARN]'
    def debug(self, msg, *args):
        if self.debugOn() is False: return
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %BasicLogger.DEBUG,
        print >>self, msg %args
    DEBUG = '[DEBUG]'
    def error(self, msg, *args):
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %BasicLogger.ERROR,
        print >>self, msg %args
    ERROR = '[ERROR]'

    def write(self, *args):
        '''Write convenience function; writes strings.
        '''
        for s in args: self.out.write(s)

_LoggerClass = BasicLogger

def setBasicLogger():
    '''Use Basic Logger. 
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(0)

def setBasicLoggerWARN():
    '''Use Basic Logger.
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(WARN)

def setBasicLoggerDEBUG():
    '''Use Basic Logger.
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(DEBUG)

def setLoggerClass(loggingClass):
    '''Set Logging Class.
    '''
    assert issubclass(loggingClass, ILogger), 'loggingClass must subclass ILogger'
    global _LoggerClass
    _LoggerClass = loggingClass

def setLevel(level=0):
    '''Set Global Logging Level.
    '''
    ILogger.level = level

def getLevel():
    return ILogger.level

def getLogger(msg):
    '''Return instance of Logging class.
    '''
    return _LoggerClass(msg)


