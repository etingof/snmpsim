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
            self._fileobj, self._file = open(priv[0], 'a'), priv[0]
        except:
            raise error.SnmpsimError(
                'Log file %s open failure: %s' % (priv[0], sys.exc_info()[1])
            )
        self._maxsize = 0
        self._maxage = 0
        self._lastrotate = 0
        if len(priv) > 1 and priv[1]:
            localtime = time.localtime()
            if priv[1][-1] in ('k', 'K'):
                self._maxsize = int(priv[1][:-1]) * 1024
            elif priv[1][-1] in ('m', 'M'):
                self._maxsize = int(priv[1][:-1]) * 1024 * 1024
            elif priv[1][-1] in ('g', 'G'):
                self._maxsize = int(priv[1][:-1]) * 1024 * 1024 * 1024
            elif priv[1][-1] in ('h', 'H'):
                self._maxage = int(priv[1][:-1]) * 3600
                self._lastrotatefun = lambda: time.mktime(localtime[:4]+(0,0)+localtime[6:])
            elif priv[1][-1] in ('d', 'D'):
                self._maxage = int(priv[1][:-1]) * 3600 * 24
                self._lastrotatefun = lambda: time.mktime(localtime[:3]+(0,0,0)+localtime[6:])
            else:
                raise error.SnmpsimError(
                    'Unknown log rotation criteria %s, use K,M,G for size and H,M for time limits' % priv[1]
                )

            self._lastrotate = self._lastrotatefun()
            self._infomsg = 'Log file %s, rotation rules are: age: %s mins, size %sKB' % (self._file, self._maxage/60, self._maxsize/1024)
            self(self._infomsg)

    def timestamp(self, now):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + \
               '.%.3d' % ((now % 1) * 1000,)

    def __call__(self, s):
        now = time.time()
        if self._maxsize:
            try:
                size = os.stat(self._file)[6]
            except:
                size = 0
        if self._maxsize and size >= self._maxsize or \
                self._maxage and now - self._lastrotate >= self._maxage:
            newName = self._file + '.%d%.2d%.2d%.2d%.2d' % time.localtime()[:5]
            if not os.path.exists(newName):
                self._fileobj.close()
                try:
                    os.rename(self._file, newName)
                except:
                    pass  # losing log
                else:
                    try: 
                        self._fileobj = open(self._file, 'a')
                    except:
                        pass # losing log
                    else:
                        self(self._infomsg)
                        if self._maxage:
                            self._lastrotate = self._lastrotatefun()

        try:
            self._fileobj.write('%s %s[%s]: %s\n' % (self.timestamp(now), self.progId, getattr(os, 'getpid', lambda x: 0)(), s))
        except IOError:
            pass # losing log

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
