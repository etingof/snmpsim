import sys
import os
import time
try:
    import syslog
except ImportError:
    syslog = None
from snmpsim import error

class AbstractLogger:
    def __init__(self, progId, *priv):
        self.progId = progId
        self.init(*priv)
    def __call__(self, s): pass
    def init(self, *priv): pass

class SyslogLogger(AbstractLogger):
    def init(self, *priv): 
        if not syslog:
            raise error.SnmpsimError('syslog not supported on this platform')
        if len(priv) < 2:
            raise error.SnmpsimError('Bad syslog params, need facility and priority')
        try:
            self.facility = getattr(syslog, 'LOG_%s' % priv[0].upper())
            self.priority = getattr(syslog, 'LOG_%s' % priv[1].upper())
        except AttributeError:
            raise error.SnmpsimError('Unknown syslog option, need facility and priority names')

        syslog.openlog(self.progId, 0, self.facility)

    def __call__(self, s): syslog.syslog(self.priority, s)

class FileLogger(AbstractLogger):
    def init(self, *priv):
        if not priv:
            raise error.SnmpsimError('Bad log file params, need filename')
        try:
            self._fileobj = open(priv[0], 'a')
        except:
            raise error.SnmpsimError(
                'Log file open failure: %s' % sys.exc_info()[1]
            )

    def timestamp(self):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + \
               '.%.3d' % int((time.time() % 1) * 1000)

    def __call__(self, s):
        self._fileobj.write('%s %s[%s]: %s\n' % (self.timestamp(), self.progId, getattr(os, 'getpid', lambda x: 0)(), s))
        self._fileobj.flush()

class ProtoStdLogger(FileLogger):
    stdfile = None
    def init(self, *priv):
        self._fileobj = self.stdfile

    def __call__(self, s): self._fileobj.write(s + '\n')

class StdoutLogger(ProtoStdLogger):
    stdfile = sys.stdout

class StderrLogger(ProtoStdLogger):
    stdfile = sys.stderr

class NullLogger(AbstractLogger): pass

gMap = {
    'syslog': SyslogLogger,
    'file': FileLogger,
    'stdout': StdoutLogger,
    'stderr': StderrLogger,
    'null': NullLogger
}

msg = lambda x: None

def setLogger(progId, *priv):
    global msg
    if priv[0] in gMap:
        msg = gMap[priv[0]](progId, *priv[1:])
    else:
        raise error.SnmpsimError('Unknown logging method "%s", known methods are: %s' % (priv[0], ', '.join(gMap.keys())))
