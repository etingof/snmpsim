import sys
import os
import time
import logging
import socket
from logging import handlers
from snmpsim import error

class AbstractLogger:
    def __init__(self, progId, *priv):
        self._logger = logging.getLogger(progId)
        self._logger.setLevel(logging.DEBUG)
        self.__ident = 0
        self.init(*priv)
    def __call__(self, s): self._logger.debug(' '*self.__ident + s)
    def incIdent(self, amount=2): 
        self.__ident += amount
    def decIdent(self, amount=2):
        self.__ident -= amount
        if self.__ident < 0:
            self.__ident = 0
    def init(self, *priv): pass

class SyslogLogger(AbstractLogger):
    def init(self, *priv): 
        if len(priv) < 1:
            raise error.SnmpsimError('Bad syslog params, need at least facility, also accept priority, host, port, socktype (tcp|udp)')
        if len(priv) < 2:
            priv = [ priv[0], 'debug' ]
        if len(priv) < 3:
            priv = [ priv[0], priv[1], 'localhost', 514, 'udp']
        if not priv[2].startswith('/'):
            if len(priv) < 4:
                priv = [ priv[0], priv[1], priv[2], 514, 'udp' ]
            if len(priv) < 5:
                priv = [ priv[0], priv[1], priv[2], 514, 'udp' ]
            priv = [ priv[0], priv[1], priv[2], int(priv[3]), priv[4] ]

        try:
            handler = handlers.SysLogHandler(priv[2].startswith('/') and priv[2] or (priv[2], int(priv[3])), priv[0].lower(), len(priv) > 4 and priv[4] == 'tcp' and socket.SOCK_STREAM or socket.SOCK_DGRAM)

        except:
            raise error.SnmpsimError('Bad syslog option(s): %s' % sys.exc_info()[1])
        handler.setFormatter(logging.Formatter('%(asctime)s %(name)s: %(message)s'))
        self._logger.addHandler(handler)

class FileLogger(AbstractLogger):
    def init(self, *priv):
        if not priv:
            raise error.SnmpsimError('Bad log file params, need filename')
        if sys.platform[:3] == 'win':
            # fix possibly corrupted absolute windows path
            if len(priv[0]) == 1 and priv[0].isalpha() and len(priv) > 1:
                priv = [ priv[0] + ':' + priv[1] ] + priv[2:]

        maxsize = 0
        maxage = None
        if len(priv) > 1 and priv[1]:
            localtime = time.localtime()
            if priv[1][-1] in ('k', 'K'):
                maxsize = int(priv[1][:-1]) * 1024
            elif priv[1][-1] in ('m', 'M'):
                maxsize = int(priv[1][:-1]) * 1024 * 1024
            elif priv[1][-1] in ('g', 'G'):
                maxsize = int(priv[1][:-1]) * 1024 * 1024 * 1024
            elif priv[1][-1] in ('h', 'H'):
                maxage = ('H', int(priv[1][:-1]))
            elif priv[1][-1] in ('d', 'D'):
                maxage = ('D', int(priv[1][:-1]))
            else:
                raise error.SnmpsimError(
                    'Unknown log rotation criteria %s, use <NNN>K,M,G for size or <NNN>H,D for time limits' % priv[1]
                )

        try:
            if maxsize:
                handler = handlers.RotatingFileHandler(priv[0], backupCount=30, maxBytes=maxsize)
            elif maxage:
                handler = handlers.TimedRotatingFileHandler(priv[0], backupCount=30, when=maxage[0], interval=maxage[1])
            else:
                handler = handlers.WatchedFileHandler(priv[0])

        except AttributeError:
            raise error.SnmpsimError(
                'Bad log rotation criteria: %s' % sys.exc_info()[1]
            )

        handler.setFormatter(logging.Formatter('%(asctime)s %(name)s: %(message)s'))
        self._logger.addHandler(handler)

        self('Log file %s, rotation rules: %s' % (priv[0], maxsize and '> %sKB' % (maxsize/1024) or maxage and '%s%s' % (maxage[1], maxage[0]) or '<none>'))

class StreamLogger(AbstractLogger):
    stream = sys.stderr
    def init(self, *priv):
        try:
            handler = logging.StreamHandler(self.stream)

        except AttributeError:
            raise error.SnmpsimError(
                'Stream logger failure: %s' % sys.exc_info()[1]
            )

        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)
 
class StdoutLogger(StreamLogger):
    stream = sys.stdout

class StderrLogger(StreamLogger):
    stream = sys.stderr

class NullLogger(AbstractLogger):
    def init(self, *priv):
        handler = logging.NullHandler()
    def __call__(self, s): pass

gMap = {
    'syslog': SyslogLogger,
    'file': FileLogger,
    'stdout': StdoutLogger,
    'stderr': StderrLogger,
    'null': NullLogger
}

msg = lambda x: None

def setLogger(progId, *priv, **options):
    global msg
    if priv[0] in gMap:
        if not isinstance(msg, AbstractLogger) or options.get('force'):
            msg = gMap[priv[0]](progId, *priv[1:])
    else:
        raise error.SnmpsimError('Unknown logging method "%s", known methods are: %s' % (priv[0], ', '.join(gMap.keys())))
