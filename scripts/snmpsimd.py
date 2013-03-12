#
# SNMP Agent Simulator
#
# Written by Ilya Etingof <ilya@glas.net>, 2010-2013
#
import os
import stat
import sys
import getopt
if sys.version_info[0] < 3 and sys.version_info[1] < 5:
    from md5 import md5
else:
    from hashlib import md5
import time
if sys.version_info[0] < 3:
    import anydbm as dbm
    from whichdb import whichdb
else:
    import dbm
    whichdb = dbm.whichdb
import bisect
from pyasn1.type import univ
from pyasn1.codec.ber import encoder, decoder
from pyasn1.compat.octets import octs2str, str2octs, int2oct
from pyasn1.error import PyAsn1Error
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asynsock.dgram import udp
try:
    from pysnmp.carrier.asynsock.dgram import udp6
except ImportError:
    udp6 = None
try:
    from pysnmp.carrier.asynsock.dgram import unix
except ImportError:
    unix = None
from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.smi import exval, indices
from pysnmp.smi.error import MibOperationError
from pysnmp.proto import rfc1902, rfc1905, api
from pysnmp import error
from pysnmp import debug
from snmpsim import __version__
from snmpsim.error import SnmpsimError
from snmpsim import confdir
from snmpsim.grammar import dump, mvc, sap, walk, snmprec

# Process command-line options

# Defaults
forceIndexBuild = False
validateData = False
v2cArch = False
v3Only = False
v3User = 'simulator'
v3AuthKey = 'auctoritas'
v3AuthProto = 'MD5'
v3PrivKey = 'privatus'
v3PrivProto = 'DES'
agentUDPv4Address = ('127.0.0.1', 161)
agentUDPv4Endpoints = []
agentUDPv6Endpoints = []
agentUNIXEndpoints = []
dataDirs = []
variationModulesDirs = []
variationModulesOptions = {}
variationModules = {}

authProtocols = {
  'MD5': config.usmHMACMD5AuthProtocol,
  'SHA': config.usmHMACSHAAuthProtocol,
  'NONE': config.usmNoAuthProtocol
}

privProtocols = {
  'DES': config.usmDESPrivProtocol,
  '3DES': config.usm3DESEDEPrivProtocol,
  'AES': config.usmAesCfb128Protocol,
  'AES128': config.usmAesCfb128Protocol,
  'AES192': config.usmAesCfb192Protocol,
  'AES256': config.usmAesCfb256Protocol,
  'NONE': config.usmNoPrivProtocol
}
 
helpMessage = 'Usage: %s [--help] [--version ] [--debug=<category>] [--data-dir=<dir>] [--cache-dir=<dir>] [--force-index-rebuild] [--validate-data] [--variation-modules-dir=<dir>] [--variation-module-options=<module[=alias][:args]>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--v2c-arch] [--v3-only] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-auth-proto=<%s>] [--v3-priv-key=<key>] [--v3-priv-proto=<%s>]' % (sys.argv[0], '|'.join(authProtocols), '|'.join(privProtocols))

try:
    opts, params = getopt.getopt(sys.argv[1:], 'h',
        ['help', 'debug=', 'device-dir=', 'data-dir=', 'cache-dir=', 'force-index-rebuild', 'validate-device-data', 'validate-data', 'variation-modules-dir=', 'variation-module-options=', 'agent-address=', 'agent-port=', 'agent-udpv4-endpoint=', 'agent-udpv6-endpoint=', 'agent-unix-endpoint=', 'v2c-arch', 'v3-only', 'v3-user=', 'v3-auth-key=', 'v3-auth-proto=', 'v3-priv-key=', 'v3-priv-proto=']
        )
except Exception:
    sys.stdout.write('%s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if params:
    sys.stdout.write('extra arguments supplied %s%s\r\n' % (params, helpMessage))
    sys.exit(-1)

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help' or \
       opt[0] == '-v' or opt[0] == '--version':
        sys.stdout.write('SNMP Simulator version %s, written by Ilya Etingof <ilya@glas.net>\r\nSoftware documentation and support at http://snmpsim.sf.net\r\n%s\r\n' % (__version__, helpMessage))
        sys.exit(-1)
    elif opt[0] == '--debug':
        debug.setLogger(debug.Debug(opt[1]))
    elif opt[0] in ('--device-dir', '--data-dir'):
        dataDirs.append(opt[1])
    elif opt[0] == '--cache-dir':
        confdir.cache = opt[1]
    elif opt[0] == '--force-index-rebuild':
        forceIndexBuild = True
    elif opt[0] in ('--validate-device-data', '--validate-data'):
        validateData = True
    elif opt[0] == '--variation-modules-dir':
        variationModulesDirs.append(opt[1])
    elif opt[0] == '--variation-module-options':
        args = opt[1].split(':')
        modName, args = args[0], args[1:]
        if '=' in modName:
            modName, alias = modName.split('=', 1)
        else:
            alias = os.path.splitext(os.path.basename(modName))[0]
        if modName not in variationModulesOptions:
            variationModulesOptions[modName] = []
        variationModulesOptions[modName].append((alias, args))
    elif opt[0] == '--agent-udpv4-endpoint':
        f = lambda h,p=161: (h, int(p))
        try:
            agentUDPv4Endpoints.append(f(*opt[1].split(':')))
        except:
            sys.stdout.write('improper IPv4/UDP endpoint %s\r\n' % opt[1])
            sys.exit(-1)
    elif opt[0] == '--agent-udpv6-endpoint':
        if not udp6:
            sys.stdout.write('This system does not support UDP/IP6\r\n')
            sys.exit(-1)
        if opt[1].find(']:') != -1 and opt[1][0] == '[':
            h, p = opt[1].split(']:')
            try:
                h, p = h[1:], int(p)
            except:
                sys.stdout.write('improper IPv6/UDP endpoint %s\r\n' % opt[1])
                sys.exit(-1)
        elif opt[1][0] == '[' and opt[1][-1] == ']':
            h, p = opt[1][1:-1], 161
        else:
            h, p = opt[1], 161
        agentUDPv6Endpoints.append((h, p))
    elif opt[0] == '--agent-unix-endpoint':
        if not unix:
            sys.stdout.write('This system does not support UNIX domain sockets\r\n')
            sys.exit(-1)
        agentUNIXEndpoints.append(opt[1])
    elif opt[0] == '--agent-address':
        agentUDPv4Address = (opt[1], agentUDPv4Address[1])
    elif opt[0] == '--agent-port':
        agentUDPv4Address = (agentUDPv4Address[0], int(opt[1]))
    elif opt[0] == '--v2c-arch':
        v2cArch = True
    elif opt[0] == '--v3-only':
        v3Only = True
    elif opt[0] == '--v3-user':
        v3User = opt[1]
    elif opt[0] == '--v3-auth-key':
        v3AuthKey = opt[1]
    elif opt[0] == '--v3-auth-proto':
        v3AuthProto = opt[1].upper()
        if v3AuthProto not in authProtocols:
            sys.stdout.write('bad v3 auth protocol %s\r\n' % v3AuthProto)
            sys.exit(-1)
    elif opt[0] == '--v3-priv-key':
        v3PrivKey = opt[1]
    elif opt[0] == '--v3-priv-proto':
        v3PrivProto = opt[1].upper()
        if v3PrivProto not in privProtocols:
            sys.stdout.write('bad v3 privacy protocol %s\r\n' % v3PrivProto)
            sys.exit(-1)

if authProtocols[v3AuthProto] == config.usmNoAuthProtocol and \
    privProtocols[v3PrivProto] != config.usmNoPrivProtocol:
        sys.stdout.write('privacy impossible without authentication\r\n')
        sys.exit(-1)

if not dataDirs:
    [ dataDirs.append(x) for x in confdir.data ]

if not variationModulesDirs:
    [ variationModulesDirs.append(x) for x in confdir.variation ]

for variationModulesDir in variationModulesDirs:
    sys.stdout.write(
        'Scanning "%s" directory for variation modules...' % variationModulesDir
    )
    if not os.path.exists(variationModulesDir):
        sys.stdout.write(' no directory\r\n')
        continue
    for dFile in os.listdir(variationModulesDir):
        if dFile[-3:] != '.py':
            continue
        _toLoad = []
        modName = os.path.splitext(os.path.basename(dFile))[0]
        if modName in variationModulesOptions:
            while variationModulesOptions[modName]:
                alias, args = variationModulesOptions[modName].pop()
                _toLoad.append((alias, args))
            del variationModulesOptions[modName]
        else:
            _toLoad.append((modName, ()))

        mod = variationModulesDir + os.path.sep + dFile

        for alias, args in _toLoad:
            if alias in variationModules:
                sys.stdout.write('\r\nvariation module %s already registered\r\n' %  alias)
                sys.exit(-1)

            ctx = { 'path': mod,
                    'alias': alias,
                    'args': args }

            try:
                if sys.version_info[0] > 2:
                    exec(compile(open(mod).read(), mod, 'exec'), ctx)
                else:
                    execfile(mod, ctx)
            except Exception:
                sys.stdout.write('\r\nvariation module %s execution failure: %s\r\n' %  (mod, sys.exc_info()[1]))
                sys.exit(-1)
            else:
                variationModules[alias] = ctx

    sys.stdout.write('%s more modules found\r\n' % len(variationModules))

if variationModulesOptions:
    sys.stdout.write('ERROR: unused options for variation modules: %s\r\n' %  ', '.join(variationModulesOptions.keys()))
    sys.exit(-1)
     
# for backward compatibility
if not agentUDPv4Endpoints and \
   not agentUDPv6Endpoints and \
   not agentUNIXEndpoints:
    agentUDPv4Endpoints.append(agentUDPv4Address)

if not os.path.exists(confdir.cache):
    try:
        os.mkdir(confdir.cache)
    except OSError:
        sys.stdout.write('ERROR: failed to create cache dir %s: %s\r\n' % (confdir.cache, sys.exc_info()[1]))
    sys.exit(-1)

# Data records

class DumpRecord:
    grammar = dump.DumpGrammar()
    ext = 'dump'

    def evaluateOid(self, oid):
        return univ.ObjectIdentifier(oid)

    def evaluateValue(self, oid, tag, value, **context):
        return oid, tag, self.grammar.tagMap[tag](value)
    
    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)
        oid = self.evaluateOid(oid)
        if context.get('oidOnly'):
            value = None
        else:
            try:
                oid, tag, value = self.evaluateValue(oid, tag, value, **context)
            except PyAsn1Error:
                raise SnmpsimError('value evaluation for %s = %r failed: %s\r\n' % (oid, value, sys.exc_info()[1]))
        return oid, value

class MvcRecord(DumpRecord):
    grammar = mvc.MvcGrammar()
    ext = 'MVC'  # an alias to .dump

class SapRecord(DumpRecord):
    grammar = sap.SapGrammar()
    ext = 'sapwalk' 

class WalkRecord(DumpRecord):
    grammar = walk.WalkGrammar()
    ext = 'snmpwalk'

class SnmprecRecord:
    grammar = snmprec.SnmprecGrammar()
    ext = 'snmprec' 

    def evaluateOid(self, oid):
        return univ.ObjectIdentifier(oid)
    
    def evaluateValue(self, oid, tag, value, **context):
        # Interpolation module reference
        if ':' in tag:
            modName, tag = tag[tag.index(':')+1:], tag[:tag.index(':')]
        else:
            modName = None
        # Unhexify
        if tag and tag[-1] == 'x':
            tag = tag[:-1]
            value = [int(value[x:x+2], 16) for x in  range(0, len(value), 2)]
        if modName:
            if 'variationModules' in context and \
                   modName in context['variationModules']:
                if 'dataValidation' in context:
                    return oid, univ.Null
                else:
                    oid, value = context['variationModules'][modName]['process'](oid, tag, value, **context)
            else:
                raise SnmpsimError('variation module "%s" referenced but not loaded\r\n' % modName)
        else:
            if 'dataValidation' in context:
                return oid, self.grammar.tagMap[tag](value)
            if not context['nextFlag'] and not context['exactMatch'] or \
               context['setFlag']:
                return context['origOid'], context['errorStatus']
        if not hasattr(value, 'tagSet'):
            value = self.grammar.tagMap[tag](value)
        return oid, value

    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)
        oid = self.evaluateOid(oid)
        if context.get('oidOnly'):
            value = None
        else:
            try:
                oid, value = self.evaluateValue(oid, tag, value, **context)
            except MibOperationError:
                raise
            except PyAsn1Error:
                raise SnmpsimError('value evaluation for %s = %r failed: %s\r\n' % (oid, value, sys.exc_info()[1]))
        return oid, value

recordSet = {
    DumpRecord.ext: DumpRecord(),
    MvcRecord.ext: MvcRecord(),
    SapRecord.ext: SapRecord(),
    WalkRecord.ext: WalkRecord(),
    SnmprecRecord.ext: SnmprecRecord()
}

class AbstractLayout:
  layout = '?'

# Data text file and OID index

class DataFile(AbstractLayout):
    layout = 'text'
    openedQueue = []
    maxQueueEntries = 31  # max number of open text and index files
    def __init__(self, textFile, textParser):
        self.__textFile = textFile
        self.__textParser = textParser
        try:
            self.__dbFile = textFile[:textFile.rindex(os.path.extsep)]
        except ValueError:
            self.__dbFile = textFile

        self.__dbFile = self.__dbFile + os.path.extsep + 'dbm'
   
        self.__dbFile = os.path.join(confdir.cache, os.path.splitdrive(self.__dbFile)[1].replace(os.path.sep, '_'))
         
        self.__db = self.__text = None
        self.__dbType = '?'
        
    def indexText(self, forceIndexBuild=False):
        textFileStamp = os.stat(self.__textFile)[8]

        # gdbm on OS X seems to voluntarily append .db, trying to catch that
        
        indexNeeded = forceIndexBuild
        
        for dbFile in (
            self.__dbFile + os.path.extsep + 'db',
            self.__dbFile
            ):
            if os.path.exists(dbFile):
                if textFileStamp < os.stat(dbFile)[8]:
                    if indexNeeded:
                        sys.stdout.write('Forced index rebuild %s\r\n' % dbFile)
                    elif not whichdb(dbFile):
                        indexNeeded = True
                        sys.stdout.write('Unsupported index format, rebuilding index %s\r\n' % dbFile)
                else:
                    indexNeeded = True
                    sys.stdout.write('Index %s out of date\r\n' % dbFile)
                break
        else:
            indexNeeded = True
            sys.stdout.write('Index %s does not exist for data file %s\r\n' % (self.__dbFile, self.__textFile))
            
        if indexNeeded:
            # these might speed-up indexing
            open_flags = 'nfu' 
            while open_flags:
                try:
                    db = dbm.open(self.__dbFile, open_flags)
                except Exception:
                    open_flags = open_flags[:-1]
                    if not open_flags:
                        raise
                else:
                    break

            text = open(self.__textFile, 'rb')

            sys.stdout.write('Building index %s for data file %s (open flags \"%s\")...' % (self.__dbFile, self.__textFile, open_flags))
            sys.stdout.flush()
        
            lineNo = 0
            offset = 0
            prevOffset = -1
            while 1:
                line = text.readline()
                if not line:
                    break
            
                lineNo += 1

                try:
                    oid, tag, val = self.__textParser.grammar.parse(line)
                except Exception:
                    db.close()
                    exc = sys.exc_info()[1]
                    try:
                        os.remove(self.__dbFile)
                    except OSError:
                        pass
                    raise Exception(
                        'Data error at %s:%d: %s' % (
                            self.__textFile, lineNo, exc
                            )
                        )

                if validateData:
                    try:
                        self.__textParser.evaluateOid(oid)
                    except Exception:
                        db.close()
                        exc = sys.exc_info()[1]
                        try:
                            os.remove(self.__dbFile)
                        except OSError:
                            pass
                        raise Exception(
                            'OID error at %s:%d: %s' % (
                                self.__textFile, lineNo, exc
                                )
                            )
                    try:
                        self.__textParser.evaluateValue(
                            oid, tag, val, dataValidation=True
                        )
                    except Exception:
                        sys.stdout.write(
                            '\r\n*** Error at line %s, value %r: %s\r\n' % \
                            (lineNo, val, sys.exc_info()[1])
                            )

                # for lines serving subtrees, type is empty in tag field
                db[oid] = '%d,%d,%d' % (offset, tag[0] == ':', prevOffset)

                if tag[0] == ':':
                    prevOffset = offset
                else:
                    prevOffset = -1   # not a subtree - no backreference

                offset += len(line)

            text.close()
            db.close()
        
            sys.stdout.write('...%d entries indexed\r\n' % (lineNo - 1,))

        self.__dbType = whichdb(self.__dbFile)

        return self

    def close(self):
        self.__text.close()
        self.__db.close()
        self.__db = self.__text = None
    
    def getHandles(self):
        if self.__db is None:
            if len(DataFile.openedQueue) > self.maxQueueEntries:
                DataFile.openedQueue[0].close()
                del DataFile.openedQueue[0]

            DataFile.openedQueue.append(self)

            self.__text = open(self.__textFile, 'rb')
            
            self.__db = dbm.open(self.__dbFile)

        return self.__text, self.__db

    def getTextFile(self): return self.__textFile

    # In-place, by-OID binary search

    def __searchOid(self, oid, eol=str2octs('\n')):
        lo = mid = 0; prev_mid = -1;
        self.__text.seek(0, 2)
        hi = sz = self.__text.tell()
        while lo < hi:
            mid = (lo+hi)//2
            self.__text.seek(mid)
            while mid:
                c = self.__text.read(1)
                if c == eol:
                    mid = mid + 1
                    break
                mid = mid - 1    # pivot stepping back in search for full line
                self.__text.seek(mid)
            if mid == prev_mid:  # loop condition due to stepping back pivot
                break
            if mid >= sz:
                return sz
            line = self.__text.readline()
            midval, _ = self.__textParser.evaluate(line, oidOnly=True)
            if midval < oid:
                lo = mid + len(line)
            elif midval > oid:
                hi = mid
            else:
                return mid
            prev_mid = mid
        if lo == mid:
            return lo
        else:
            return hi

    def processVarBinds(self, varBinds, nextFlag=False, setFlag=False):
        rspVarBinds = []

        if nextFlag:
            errorStatus = exval.endOfMib
        else:
            errorStatus = exval.noSuchInstance

        text, db = self.getHandles()
       
        varsRemaining = varsTotal = len(varBinds)
         
        for oid, val in varBinds:
            textOid = str(
                univ.OctetString('.'.join([ '%s' % x for x in oid ]))
            )

            try:
                offset, subtreeFlag, prevOffset = db[textOid].split(str2octs(','))
                exactMatch = True
                subtreeFlag = int(subtreeFlag)
            except KeyError:
                offset = self.__searchOid(oid)
                subtreeFlag = exactMatch = False

            offset = int(offset)

            text.seek(offset)

            varsRemaining -= 1

            line = text.readline()  # matched line

            while True:
                if exactMatch:
                    if nextFlag and not subtreeFlag:
                        _nextLine = text.readline() # next line
                        if _nextLine:
                            _nextOid, _ = self.__textParser.evaluate(_nextLine, oidOnly=True)
                            _, subtreeFlag, _ = db[str(_nextOid)].split(str2octs(','))
                            subtreeFlag = int(subtreeFlag)
                        line = _nextLine
                else: # search function above always rounds up to the next OID
                    if line:
                        _oid, _  = self.__textParser.evaluate(
                            line, oidOnly=True
                        )
                        _, _, _prevOffset = db[str(_oid)].split(str2octs(','))
                        _prevOffset = int(_prevOffset)

                        if _prevOffset >= 0:  # previous line serves a subtree
                            text.seek(_prevOffset)
                            _prevLine = text.readline()
                            _prevOid, _ = self.__textParser.evaluate(
                                _prevLine, oidOnly=True
                            )
                            if _prevOid.isPrefixOf(oid):
                                # use previous line to the matched one
                                line = _prevLine
                                subtreeFlag = True

                if not line:
                    _oid = oid
                    _val = errorStatus
                    break

                try:
                    _oid, _val = self.__textParser.evaluate(line, setFlag=setFlag, origOid=oid, origValue=val, dataFile=self.getTextFile(), subtreeFlag=subtreeFlag, nextFlag=nextFlag, exactMatch=exactMatch, errorStatus=errorStatus, varsTotal=varsTotal, varsRemaining=varsRemaining, variationModules=variationModules)
                    if _val is exval.endOfMib:
                        exactMatch = True
                        subtreeFlag = False
                        continue
                except MibOperationError:
                    raise
                except Exception:
                    _oid = oid
                    _val = errorStatus
                    sys.stdout.write(
                        'data error at %s for %s: %s\r\n' % (self, textOid, sys.exc_info()[1])
                    )

                break

            rspVarBinds.append((_oid, _val))

        return rspVarBinds
 
    def __str__(self):
        return 'Data file %s, %s-indexed, %s' % (
            self.__textFile, self.__dbType, self.__db and 'opened' or 'closed'
            )

# Collect data files

def getDataFiles(tgtDir, topLen=None):
    if topLen is None:
        topLen = len(tgtDir.split(os.path.sep))
    dirContent = []
    for dFile in os.listdir(tgtDir):
        fullPath = tgtDir + os.path.sep + dFile
        inode = os.lstat(fullPath)
        if stat.S_ISLNK(inode.st_mode):
            relPath = fullPath.split(os.path.sep)[topLen:]
            fullPath = os.readlink(fullPath)
            if not os.path.isabs(fullPath):
                fullPath = tgtDir + os.path.sep + fullPath
            inode = os.stat(fullPath)
        else:
            relPath = fullPath.split(os.path.sep)[topLen:]
        if stat.S_ISDIR(inode.st_mode):
            dirContent = dirContent + getDataFiles(fullPath, topLen)
            continue            
        if not stat.S_ISREG(inode.st_mode):
            continue
        dExt = os.path.splitext(dFile)[1][1:]
        if dExt not in recordSet:
            continue
        dirContent.append((fullPath,
                           recordSet[dExt],
                           os.path.splitext(os.path.join(*relPath))[0]))
    return dirContent

# Lightweignt MIB instrumentation (API-compatible with pysnmp's)

class MibInstrumController:
    def __init__(self, dataFile):
        self.__dataFile = dataFile

    def __str__(self): return str(self.__dataFile)

    def readVars(self, varBinds, acInfo=None):
        return self.__dataFile.processVarBinds(varBinds, False)

    def readNextVars(self, varBinds, acInfo=None):
        return self.__dataFile.processVarBinds(varBinds, True)

    def writeVars(self, varBinds, acInfo=None):
        return self.__dataFile.processVarBinds(varBinds, False, True)

# Data files index as a MIB instrumentaion at a dedicated SNMP context

class DataIndexInstrumController:
    indexSubOid = (1,)
    def __init__(self, baseOid=(1, 3, 6, 1, 4, 1, 20408, 999)):
        self.__db = indices.OidOrderedDict()
        self.__indexOid = baseOid + self.indexSubOid
        self.__idx = 1

    def readVars(self, varBinds, acInfo=None):
        return [ (vb[0], self.__db.get(vb[0], exval.noSuchInstance)) for vb in varBinds ]

    def __getNextVal(self, key, default):
        try:
            key = self.__db.nextKey(key)
        except KeyError:
            return key, default
        else:
            return key, self.__db[key]
                                                            
    def readNextVars(self, varBinds, acInfo=None):
        return [ self.__getNextVal(vb[0], exval.endOfMib) for vb in varBinds ]        

    def writeVars(self, varBinds, acInfo=None):
        return [ (vb[0], exval.noSuchInstance) for vb in varBinds ]        
    
    def addDataFile(self, *args):
        for idx in range(len(args)):
            self.__db[
                self.__indexOid + (idx+1, self.__idx)
                ] = rfc1902.OctetString(args[idx])
        self.__idx = self.__idx + 1

dataIndexInstrumController = DataIndexInstrumController()

mibInstrumControllerSet = {
    DataFile.layout: MibInstrumController
}

# Suggest variations of context name based on request data
def probeContext(transportDomain, transportAddress, contextName):
    candidate = [
        contextName, '.'.join([ str(x) for x in transportDomain ])
    ]
    if transportDomain[:len(udp.domainName)] == udp.domainName:
        candidate.append(transportAddress[0])
    elif udp6 and transportDomain[:len(udp6.domainName)] == udp6.domainName:
        candidate.append(
            str(transportAddress[0]).replace(':', '_')
        )
    elif unix and transportDomain[:len(unix.domainName)] == unix.domainName:
        candidate.append(transportAddress)

    candidate = [ str(x) for x in candidate if x ]

    while candidate:
        yield rfc1902.OctetString(
                  os.path.normpath(os.path.sep.join(candidate))
              ).asOctets()
        del candidate[-1]
 
if not v2cArch:
    def probeHashContext(self, snmpEngine, stateReference, contextName):
        transportDomain, transportAddress = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)

        for probedContextName in probeContext(transportDomain, transportAddress, contextName):
            probedContextName = md5(probedContextName).hexdigest()
            try:
                self.snmpContext.getMibInstrum(probedContextName)
            except error.PySnmpError:
                pass
            else:
                return probedContextName
        return contextName

    class GetCommandResponder(cmdrsp.GetCommandResponder):
        def handleMgmtOperation(
                self, snmpEngine, stateReference, contextName, PDU, acInfo
            ):
            cmdrsp.GetCommandResponder.handleMgmtOperation(
                self, snmpEngine, stateReference, 
                probeHashContext(self, snmpEngine, stateReference, contextName),
                PDU, acInfo
            )

    class SetCommandResponder(cmdrsp.SetCommandResponder):
        def handleMgmtOperation(
                self, snmpEngine, stateReference, contextName, PDU, acInfo
            ):
            cmdrsp.SetCommandResponder.handleMgmtOperation(
                self, snmpEngine, stateReference, 
                probeHashContext(self, snmpEngine, stateReference, contextName),
                PDU, acInfo
            )

    class NextCommandResponder(cmdrsp.NextCommandResponder):
        def handleMgmtOperation(
                self, snmpEngine, stateReference, contextName, PDU, acInfo
            ):
            cmdrsp.NextCommandResponder.handleMgmtOperation(
                self, snmpEngine, stateReference, 
                probeHashContext(self, snmpEngine, stateReference, contextName),
                PDU, acInfo
            )

    class BulkCommandResponder(cmdrsp.BulkCommandResponder):
        def handleMgmtOperation(
                self, snmpEngine, stateReference, contextName, PDU, acInfo
            ):
            cmdrsp.BulkCommandResponder.handleMgmtOperation(
                self, snmpEngine, stateReference, 
                probeHashContext(self, snmpEngine, stateReference, contextName),
                PDU, acInfo
            )

# Basic SNMP engine configuration

if v2cArch:
    contexts = { univ.OctetString('index'): dataIndexInstrumController }
else:
    snmpEngine = engine.SnmpEngine()

    config.addContext(snmpEngine, '')

    snmpContext = context.SnmpContext(snmpEngine)
        
    config.addV3User(
        snmpEngine,
        v3User,
        authProtocols[v3AuthProto], v3AuthKey,
        privProtocols[v3PrivProto], v3PrivKey
        )

if variationModules:
    sys.stdout.write('Initializing variation modules:\r\n')
    for name, body in variationModules.items():
        sys.stdout.write('    %s...  ' % name)
        for x in ('init', 'process', 'shutdown'):
            if x not in body:
                sys.stdout.write('error: missing %s handler!\r\n' % x)
                sys.exit(-1)
        try:
            body['init'](not v2cArch and snmpEngine or None, *body['args'])
        except Exception:
            sys.stdout.write('FAILED: %s\r\n' % sys.exc_info()[1])
        else:
            sys.stdout.write('OK\r\n')

# Build pysnmp Managed Objects base from data files information

_mibInstrums = {}

for dataDir in dataDirs:
    sys.stdout.write(
        'Scanning "%s" directory for %s data files...' % (dataDir, ','.join([' *%s%s' % (os.path.extsep, x.ext) for x in recordSet.values()]))
    )
    if not os.path.exists(dataDir):
        sys.stdout.write(' no directory\r\n')
        continue
    sys.stdout.write('\r\n%s\r\n' % ('='*66,))
    for fullPath, textParser, communityName in getDataFiles(dataDir):
        if fullPath in _mibInstrums:
            mibInstrum = _mibInstrums[fullPath]
            sys.stdout.write('Shared data %s\r\n' % (mibInstrum,))
        else:
            dataFile = DataFile(fullPath, textParser).indexText(forceIndexBuild)
            mibInstrum = mibInstrumControllerSet[dataFile.layout](dataFile)

            _mibInstrums[fullPath] = mibInstrum
            sys.stdout.write('%s\r\n' % (mibInstrum,))

        sys.stdout.write('SNMPv1/2c community name: %s\r\n' % (communityName,))

        if v2cArch:
            contexts[univ.OctetString(communityName)] = mibInstrum
        
            dataIndexInstrumController.addDataFile(
                fullPath, communityName
            )
        else:
            agentName = contextName = md5(univ.OctetString(communityName).asOctets()).hexdigest()

            if not v3Only:
                config.addV1System(
                    snmpEngine, agentName, communityName, contextName=contextName
                )

            snmpContext.registerContextName(contextName, mibInstrum)
                 
            dataIndexInstrumController.addDataFile(
                fullPath, communityName, contextName
            )
                 
            sys.stdout.write('SNMPv3 context name: %s\r\n' % (contextName,))
        
        sys.stdout.write('%s\r\n' % ('-+' * 33,))
        
del _mibInstrums

if v2cArch:
    def getBulkHandler(varBinds, nonRepeaters, maxRepetitions, readNextVars):
        if nonRepeaters < 0: nonRepeaters = 0
        if maxRepetitions < 0: maxRepetitions = 0
        N = min(nonRepeaters, len(varBinds))
        M = int(maxRepetitions)
        R = max(len(varBinds)-N, 0)
        if nonRepeaters:
            rspVarBinds = readNextVars(varBinds[:int(nonRepeaters)])
        else:
            rspVarBinds = []
        if M and R:
            for i in range(N,  R):
                varBind = varBinds[i]
                for r in range(1, M):
                    rspVarBinds.extend(readNextVars((varBind,)))
                    varBind = rspVarBinds[-1]

        return rspVarBinds
 
    def commandResponderCbFun(transportDispatcher, transportDomain,
                              transportAddress, wholeMsg):
        while wholeMsg:
            msgVer = api.decodeMessageVersion(wholeMsg)
            if msgVer in api.protoModules:
                pMod = api.protoModules[msgVer]
            else:
                sys.stdout.write('Unsupported SNMP version %s\r\n' % (msgVer,))
                return
            reqMsg, wholeMsg = decoder.decode(
                wholeMsg, asn1Spec=pMod.Message(),
                )

            communityName = reqMsg.getComponentByPosition(1)
            for communityName in probeContext(transportDomain, transportAddress, communityName):
                if communityName in contexts:
                    break
            else:
                return wholeMsg
            
            rspMsg = pMod.apiMessage.getResponse(reqMsg)
            rspPDU = pMod.apiMessage.getPDU(rspMsg)        
            reqPDU = pMod.apiMessage.getPDU(reqMsg)
    
            if reqPDU.isSameTypeWith(pMod.GetRequestPDU()):
                backendFun = contexts[communityName].readVars
            elif reqPDU.isSameTypeWith(pMod.SetRequestPDU()):
                backendFun = contexts[communityName].writeVars
            elif reqPDU.isSameTypeWith(pMod.GetNextRequestPDU()):
                backendFun = contexts[communityName].readNextVars
            elif hasattr(pMod, 'GetBulkRequestPDU') and \
                     reqPDU.isSameTypeWith(pMod.GetBulkRequestPDU()):
                if not msgVer:
                    sys.stdout.write('GETBULK over SNMPv1 from %s:%s\r\n' % (
                        transportDomain, transportAddress
                        ))
                    return wholeMsg
                backendFun = lambda varBinds: getBulkHandler(varBinds,
                    pMod.apiBulkPDU.getNonRepeaters(reqPDU),
                    pMod.apiBulkPDU.getMaxRepetitions(reqPDU),
                    contexts[communityName].readNextVars)
            else:
                sys.stdout.write('Unsuppored PDU type %s from %s:%s\r\n' % (
                    reqPDU.__class__.__name__, transportDomain,
                    transportAddress
                    ))
                return wholeMsg
    
            varBinds = backendFun(
                pMod.apiPDU.getVarBinds(reqPDU)
                )

            # Poor man's v2c->v1 translation
            errorMap = {  rfc1902.Counter64.tagSet: 5,
                          rfc1905.NoSuchObject.tagSet: 2,
                          rfc1905.NoSuchInstance.tagSet: 2,
                          rfc1905.EndOfMibView.tagSet: 2  }
 
            if not msgVer:
                for idx in range(len(varBinds)):
                    oid, val = varBinds[idx]
                    if val.tagSet in errorMap:
                        varBinds = pMod.apiPDU.getVarBinds(reqPDU)
                        pMod.apiPDU.setErrorStatus(rspPDU, errorMap[val.tagSet])
                        pMod.apiPDU.setErrorIndex(rspPDU, idx+1)
                        break

            pMod.apiPDU.setVarBinds(rspPDU, varBinds)
            
            transportDispatcher.sendMessage(
                encoder.encode(rspMsg), transportDomain, transportAddress
                )
            
        return wholeMsg

    # Configure access to data index
    
    contexts['index'] = dataIndexInstrumController
    
    # Configure socket server
   
    sys.stdout.write('Listening at:\r\n')
 
    transportDispatcher = AsynsockDispatcher()
    for idx in range(len(agentUDPv4Endpoints)):
        transportDispatcher.registerTransport(
                udp.domainName + (idx,),
                udp.UdpTransport().openServerMode(agentUDPv4Endpoints[idx])
            )
        sys.stdout.write('  UDP/IPv4 endpoint %s:%s, transport ID %s\r\n' % (agentUDPv4Endpoints[idx] + ('.'.join([str(x) for x in udp.domainName + (idx,)]),)))
    for idx in range(len(agentUDPv6Endpoints)):
        transportDispatcher.registerTransport(
                udp6.domainName + (idx,),
                udp6.Udp6Transport().openServerMode(agentUDPv6Endpoints[idx])
            )
        sys.stdout.write('  UDP/IPv6 endpoint %s:%s, transport ID %s\r\n' % (agentUDPv6Endpoints[idx] + ('.'.join([str(x) for x in udp6.domainName + (idx,)]),)))
    for idx in range(len(agentUNIXEndpoints)):
        transportDispatcher.registerTransport(
                unix.domainName + (idx,),
                unix.UnixTransport().openServerMode(agentUNIXEndpoints[idx])
            )
        sys.stdout.write('  UNIX domain endpoint %s, transport ID %s\r\n' % (agentUNIXEndpoints[idx], '.'.join([str(x) for x in unix.domainName + (idx,)])))
    transportDispatcher.registerRecvCbFun(commandResponderCbFun)
else:
    sys.stdout.write('SNMPv3 credentials:\r\nUsername: %s\r\n' % v3User)
    if authProtocols[v3AuthProto] != config.usmNoAuthProtocol:
        sys.stdout.write('Authentication key: %s\r\nAuthentication protocol: %s\r\n' % (v3AuthKey, v3AuthProto))
        if privProtocols[v3PrivProto] != config.usmNoPrivProtocol:
            sys.stdout.write('Encryption (privacy) key: %s\r\nEncryption protocol: %s\r\n' % (v3PrivKey, v3PrivProto))

    # Configure access to data index

    config.addV1System(snmpEngine, 'index',
                       'index', contextName='index')

    snmpContext.registerContextName(
        'index', dataIndexInstrumController
        )

    # Configure socket server

    sys.stdout.write('Listening at:\r\n')

    for idx in range(len(agentUDPv4Endpoints)):
        config.addSocketTransport(
            snmpEngine,
            udp.domainName + (idx,),
            udp.UdpTransport().openServerMode(agentUDPv4Endpoints[idx])
        )
        sys.stdout.write('  UDP/IPv4 endpoint %s:%s, transport ID %s\r\n' % (agentUDPv4Endpoints[idx] + ('.'.join([str(x) for x in udp.domainName + (idx,)]),)))
    for idx in range(len(agentUDPv6Endpoints)):
        config.addSocketTransport(
            snmpEngine,
            udp6.domainName + (idx,),
            udp6.Udp6Transport().openServerMode(agentUDPv6Endpoints[idx])
        )
        sys.stdout.write('  UDP/IPv6 endpoint %s:%s, transport ID %s\r\n' % (agentUDPv6Endpoints[idx] + ('.'.join([str(x) for x in udp6.domainName + (idx,)]),)))
    for idx in range(len(agentUNIXEndpoints)):
        config.addSocketTransport(
            snmpEngine,
            unix.domainName + (idx,),
            unix.UnixTransport().openServerMode(agentUNIXEndpoints[idx])
        )
        sys.stdout.write('  UNIX domain endpoint %s, transport ID %s\r\n' % (agentUNIXEndpoints[idx], '.'.join([str(x) for x in unix.domainName + (idx,)])))

    # SNMP applications

    GetCommandResponder(snmpEngine, snmpContext)
    SetCommandResponder(snmpEngine, snmpContext)
    NextCommandResponder(snmpEngine, snmpContext)
    BulkCommandResponder(snmpEngine, snmpContext)

    transportDispatcher = snmpEngine.transportDispatcher

# Run mainloop

transportDispatcher.jobStarted(1) # server job would never finish

# Python 2.4 does not support the "finally" clause

exc_info = None

try:
    transportDispatcher.runDispatcher()
except KeyboardInterrupt:
    sys.stdout.write('Process terminated\r\n')
except Exception:
    exc_info = sys.exc_info()

if variationModules:
    sys.stdout.write('Shutting down variation modules:\r\n')
    for name, body in variationModules.items():
        sys.stdout.write('    %s...  ' % name)
        try:
            body['shutdown'](not v2cArch and snmpEngine or None, *body['args'])
        except Exception:
            sys.stdout.write('FAILED: %s\r\n' % sys.exc_info()[1])
        else:
            sys.stdout.write('OK\r\n')

transportDispatcher.closeDispatcher()

if exc_info:
    e = exc_info[0](exc_info[1])
    e.__traceback__ = exc_info[2]
    raise e
