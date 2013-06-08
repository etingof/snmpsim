#!/usr/bin/env python
#
# SNMP Agent Simulator
#
# Written by Ilya Etingof <ilya@glas.net>, 2010-2013
#
import os
import stat
import sys
import getopt
import traceback
if sys.version_info[0] < 3 and sys.version_info[1] < 5:
    from md5 import md5
else:
    from hashlib import md5
from pyasn1.type import univ
from pyasn1.codec.ber import encoder, decoder
from pyasn1.compat.octets import str2octs
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
from snmpsim.error import SnmpsimError, NoDataNotification
from snmpsim import confdir, log, daemon
from snmpsim.record import dump, mvc, sap, walk, snmprec
from snmpsim.record.search.file import searchRecordByOid
from snmpsim.record.search.database import RecordIndex

# Settings
forceIndexBuild = False
validateData = False
v2cArch = False
v3Only = False
v3Users = []
v3AuthKeys = {}
v3AuthProtos = {}
v3PrivKeys = {}
v3PrivProtos = {}
pidFile = '/var/run/snmpsim/snmpsimd.pid'
foregroundFlag = True
procUser = procGroup = None
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

# Transport endpoints collection

class TransportEndpointsBase:
    def __init__(self):
        self.__endpoints = []

    def add(self, addr):
        self.__endpoints.append(
            self._addEndpoint(addr)
        )

    def load(self, filename):
        for rec in open(filename).read().split():
            self.add(rec)
        
    def _addEndpoint(self, addr): raise NotImplementedError()

    def __len__(self): return len(self.__endpoints)
    def __getitem__(self, i): return self.__endpoints[i]

class IPv4TransportEndpoints(TransportEndpointsBase):
    def _addEndpoint(self, addr):
        f = lambda h,p=161: (h, int(p))
        try:
            h, p = f(*addr.split(':'))
        except:
            raise SnmpsimError('improper/busy IPv4/UDP endpoint %s' % addr)
        return udp.UdpTransport().openServerMode((h, p)), addr

agentUDPv4Endpoints = IPv4TransportEndpoints()
 
class IPv6TransportEndpoints(TransportEndpointsBase):
    def _addEndpoint(self, addr):
        if not udp6:
            raise SnmpsimError('This system does not support UDP/IP6')
        if addr.find(']:') != -1 and addr[0] == '[':
            h, p = addr.split(']:')
            try:
                h, p = h[1:], int(p)
            except:
                raise SnmpsimError('improper/busy IPv6/UDP endpoint %s' % addr)
        elif addr[0] == '[' and addr[-1] == ']':
            h, p = addr[1:-1], 161
        else:
            h, p = addr, 161
        return udp6.Udp6Transport().openServerMode((h, p)), addr
 
agentUDPv6Endpoints = IPv6TransportEndpoints()

class UnixTransportEndpoints(TransportEndpointsBase):
    def _addEndpoint(self, addr):
        if not unix:
            raise SnmpsimError('This system does not support UNIX domain sockets')
        return unix.UnixTransport().openServerMode(addr), addr

agentUNIXEndpoints = UnixTransportEndpoints()

# Extended snmprec record handler

class SnmprecRecord(snmprec.SnmprecRecord):
    def evaluateValue(self, oid, tag, value, **context):
        # Variation module reference
        if ':' in tag:
            modName, tag = tag[tag.index(':')+1:], tag[:tag.index(':')]
        else:
            modName = None

        if modName:
            if 'variationModules' in context and \
                   modName in context['variationModules']:
                if 'dataValidation' in context:
                    return oid, tag, univ.Null
                else:
                    if context['setFlag']:
                        hexvalue = self.grammar.hexifyValue(context['origValue'])
                        if hexvalue is not None:
                            context['hexvalue'] = hexvalue
                            context['hextag'] = self.grammar.getTagByType(context['origValue']) + 'x'

                    # prepare agent and record contexts on first reference
                    ( variationModule,
                      agentContexts,
                      recordContexts ) = context['variationModules'][modName]
                    if context['dataFile'] not in agentContexts:
                        agentContexts[context['dataFile']] = {}
                    variationModule['agentContext'] = agentContexts[context['dataFile']]
                    if oid not in recordContexts:
                        recordContexts[oid] = {}
                    variationModule['recordContext'] = recordContexts[oid]

                    # invoke variation module
                    oid, tag, value = variationModule['variate'](oid, tag, value, **context)
            else:
                raise SnmpsimError('Variation module "%s" referenced but not loaded\r\n' % modName)

        if not modName:
            if 'dataValidation' in context:
                snmprec.SnmprecRecord.evaluateValue(
                    self, oid, tag, value, **context
                )

            if not context['nextFlag'] and not context['exactMatch'] or \
                   context['setFlag']:
                return context['origOid'], tag, context['errorStatus']

        if not hasattr(value, 'tagSet'):  # not already a pyasn1 object
            return snmprec.SnmprecRecord.evaluateValue(
                       self, oid, tag, value, **context
                   )

        return oid, tag, value

    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)
        oid = self.evaluateOid(oid)
        if context.get('oidOnly'):
            value = None
        else:
            try:
                oid, tag, value = self.evaluateValue(oid, tag, value, **context)
            except NoDataNotification:
                raise
            except MibOperationError:
                raise
            except PyAsn1Error:
                raise SnmpsimError('value evaluation for %s = %r failed: %s\r\n' % (oid, value, sys.exc_info()[1]))
        return oid, value

recordSet = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
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
        self.__recordIndex = RecordIndex(textFile, textParser)
        self.__textParser = textParser
        self.__textFile = textFile
        
    def indexText(self, forceIndexBuild=False):
        self.__recordIndex.create(forceIndexBuild, validateData)
        return self

    def close(self):
        self.__recordIndex.close()
    
    def getHandles(self):
        if not self.__recordIndex.isOpen():
            if len(DataFile.openedQueue) > self.maxQueueEntries:
                log.msg('Closing %s' % self)
                DataFile.openedQueue[0].close()
                del DataFile.openedQueue[0]

            DataFile.openedQueue.append(self)

            log.msg('Opening %s' % self)

            self.__recordIndex.open()

        return self.__recordIndex.getHandles()

    def processVarBinds(self, varBinds, nextFlag=False, setFlag=False):
        rspVarBinds = []

        if nextFlag:
            errorStatus = exval.endOfMib
        else:
            errorStatus = exval.noSuchInstance

        text, db = self.getHandles()
       
        varsRemaining = varsTotal = len(varBinds)
        
        log.msg('Request var-binds: %s, flags: %s, %s' % (', '.join(['%s=<%s>' % (vb[0], vb[1].prettyPrint()) for vb in varBinds]), nextFlag and 'NEXT' or 'EXACT', setFlag and 'SET' or 'GET'))

        for oid, val in varBinds:
            textOid = str(
                univ.OctetString('.'.join([ '%s' % x for x in oid ]))
            )

            try:
                line = self.__recordIndex.lookup(
                    str(univ.OctetString('.'.join([ '%s' % x for x in oid ])))
                )
            except KeyError:
                offset = searchRecordByOid(oid, text, self.__textParser)
                subtreeFlag = exactMatch = False
            else:
                offset, subtreeFlag, prevOffset = line.split(str2octs(','))
                subtreeFlag, exactMatch = int(subtreeFlag), True

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
                            try:
                                _, subtreeFlag, _ = self.__recordIndex.lookup(str(_nextOid)).split(str2octs(','))
                            except KeyError:
                                log.msg('data error for %s at %s, index broken?' % (self, _nextOid))
                                line = ''  # fatal error
                            else:
                                subtreeFlag = int(subtreeFlag)
                                line = _nextLine
                        else:
                            line = _nextLine
                else: # search function above always rounds up to the next OID
                    if line:
                        _oid, _  = self.__textParser.evaluate(
                            line, oidOnly=True
                        )
                    else:  # eom
                        _oid = 'last'

                    try:
                        _, _, _prevOffset = self.__recordIndex.lookup(str(_oid)).split(str2octs(','))
                    except KeyError:
                        log.msg('data error for %s at %s, index broken?' % (self, _oid))
                        line = ''  # fatal error
                    else:
                        _prevOffset = int(_prevOffset)

                        # previous line serves a subtree?
                        if _prevOffset >= 0:
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
                    _oid, _val = self.__textParser.evaluate(line, setFlag=setFlag, origOid=oid, origValue=val, dataFile=self.__textFile, subtreeFlag=subtreeFlag, nextFlag=nextFlag, exactMatch=exactMatch, errorStatus=errorStatus, varsTotal=varsTotal, varsRemaining=varsRemaining, variationModules=variationModules)
                    if _val is exval.endOfMib:
                        exactMatch = True
                        subtreeFlag = False
                        continue
                except NoDataNotification:
                    raise error.PySnmpError()
                except MibOperationError:
                    raise
                except Exception:
                    _oid = oid
                    _val = errorStatus
                    log.msg('data error at %s for %s: %s' % (self, textOid, sys.exc_info()[1]))

                break

            rspVarBinds.append((_oid, _val))

        log.msg('Response var-binds: %s' % (', '.join(['%s=<%s>' % (vb[0], vb[1].prettyPrint()) for vb in rspVarBinds])))

        return rspVarBinds
 
    def __str__(self): return '%s controller' % self.__textFile

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
        dirContent.append(
            (fullPath,
             recordSet[dExt],
             os.path.splitext(os.path.join(*relPath))[0].replace(os.path.sep, '/'))
        )
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

    def __str__(self): return '<index> controller'

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
        yield rfc1902.OctetString(os.path.normpath(os.path.sep.join(candidate)).replace(os.path.sep, '/')).asOctets()
        del candidate[-1]
 
if not v2cArch:
    def probeHashContext(self, snmpEngine, stateReference, contextName):
        transportDomain, transportAddress = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)

        for candidate in probeContext(transportDomain, transportAddress, contextName):
            probedContextName = md5(candidate).hexdigest()
            try:
                mibInstrum = self.snmpContext.getMibInstrum(probedContextName)
            except error.PySnmpError:
                pass
            else:
                log.msg('Using %s selected by candidate %s; transport ID %s, source address %s, context name "%s"' % (mibInstrum, candidate, univ.ObjectIdentifier(transportDomain), transportAddress[0], probedContextName))
                return probedContextName

        log.msg('Using %s selected by contextName "%s", transport ID %s, source address %s' % (self.snmpContext.getMibInstrum(contextName), contextName, univ.ObjectIdentifier(transportDomain), transportAddress[0]))

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

# main script body starts here

helpMessage = """\
Usage: %s [--help]
    [--version ]
    [--debug=<%s>]
    [--daemonize]
    [--process-user=<uname>] [--process-group=<gname>]
    [--logging-method=<stdout|stderr|syslog|file>[:args>]]
    [--data-dir=<dir>]
    [--cache-dir=<dir>]
    [--variation-modules-dir=<dir>]
    [--variation-module-options=<module[=alias][:args]>] 
    [--force-index-rebuild]
    [--validate-data]
    [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>]
    [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>]
    [--agent-unix-endpoint=</path/to/named/pipe>]
    [--agent-udpv4-endpoints-list=<file>]
    [--agent-udpv6-endpoints-list=<file>]
    [--agent-unix-endpoints-list=<file>]
    [--v2c-arch]
    [--v3-only]
    [--v3-user=<username>]
    [--v3-auth-key=<key>]
    [--v3-auth-proto=<%s>]
    [--v3-priv-key=<key>]
    [--v3-priv-proto=<%s>]""" % (
        sys.argv[0],
        '|'.join([ x for x in debug.flagMap.keys() if x != 'mibview' ]),
        '|'.join(authProtocols),
        '|'.join(privProtocols)
    )

try:
    opts, params = getopt.getopt(sys.argv[1:], 'hv',
        ['help', 'version', 'debug=', 'daemonize', 'process-user=', 'process-group=', 'logging-method=', 'device-dir=', 'data-dir=', 'cache-dir=', 'force-index-rebuild', 'validate-device-data', 'validate-data', 'variation-modules-dir=', 'variation-module-options=', 'agent-address=', 'agent-port=', 'agent-udpv4-endpoint=', 'agent-udpv6-endpoint=', 'agent-unix-endpoint=', 'agent-udpv4-endpoints-list=', 'agent-udpv6-endpoints-list=', 'agent-unix-endpoints-list=', 'v2c-arch', 'v3-only', 'v3-user=', 'v3-auth-key=', 'v3-auth-proto=', 'v3-priv-key=', 'v3-priv-proto=']
        )
except Exception:
    sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if params:
    sys.stderr.write('ERROR: extra arguments supplied %s\r\n%s\r\n' % (params, helpMessage))
    sys.exit(-1)

log.setLogger('snmpsimd', 'stdout')

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  SNMP Agents Simulation tool. Responds to SNMP requests, variate responses
  based on transport addresses, SNMP community name or SNMPv3 context name.
  Can implement highly complex behavior through variation modules.
Documentation:
  http://snmpsim.sourceforge.net/simulating-agents.html
%s
""" % helpMessage)
        sys.exit(-1)
    if opt[0] == '-v' or opt[0] == '--version':
        import snmpsim, pysnmp, pyasn1
        sys.stderr.write("""\
SNMP Simulator version %s, written by Ilya Etingof <ilya@glas.net>
Using foundation libraries: pysnmp %s, pyasn1 %s.
Software documentation and support at http://snmpsim.sf.net
%s
""" % (snmpsim.__version__, hasattr(pysnmp, '__version__') and pysnmp.__version__ or 'unknown', hasattr(pyasn1, '__version__') and pyasn1.__version__ or 'unknown', helpMessage))
        sys.exit(-1)
    elif opt[0] == '--debug':
        debug.setLogger(debug.Debug(opt[1]))
    elif opt[0] == '--daemonize':
        foregroundFlag = False
    elif opt[0] == '--process-user':
        procUser = opt[1]
    elif opt[0] == '--process-group':
        procGroup = opt[1]
    elif opt[0] == '--logging-method':
        try:
            log.setLogger('snmpsimd', *opt[1].split(':'))
        except SnmpsimError:
            sys.stderr.write('%s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] in ('--device-dir', '--data-dir'):
        confdir.data.insert(0, opt[1])
    elif opt[0] == '--cache-dir':
        confdir.cache = opt[1]
    elif opt[0] == '--force-index-rebuild':
        forceIndexBuild = True
    elif opt[0] in ('--validate-device-data', '--validate-data'):
        validateData = True
    elif opt[0] == '--variation-modules-dir':
        confdir.variation.insert(0, opt[1])
    elif opt[0] == '--variation-module-options':
        args = opt[1].split(':', 1)
        try:
            modName, args = args[0], args[1]
        except:
            sys.stderr.write('ERROR: improper variation module options: %s\r\n%s\r\n' % (opt[1], helpMessage))
            sys.exit(-1)
        if '=' in modName:
            modName, alias = modName.split('=', 1)
        else:
            alias = os.path.splitext(os.path.basename(modName))[0]
        if modName not in variationModulesOptions:
            variationModulesOptions[modName] = []
        variationModulesOptions[modName].append((alias, args))
    elif opt[0] == '--agent-udpv4-endpoint':
        try:
            agentUDPv4Endpoints.add(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-udpv6-endpoint':
        try:
            agentUDPv6Endpoints.add(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-unix-endpoint':
        try:
            agentUNIXEndpoints.add(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-udpv4-endpoints-list':
        try:
            agentUDPv4Endpoints.load(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-udpv6-endpoints-list':
        try:
            agentUDPv6Endpoints.load(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-unix-endpoints-list':
        try:
            agentUNIXEndpoints.load(opt[1])
        except:
            sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-address':
        sys.stderr.write('ERROR: use --agent-udpv4-endpoint=%s option instead of --agent-address\r\n%s\r\n' % (opt[1], helpMessage))
        sys.exit(-1)
    elif opt[0] == '--agent-port':
        sys.stderr.write('ERROR: use --agent-udpv4-endpoint=0.0.0.0:%s option instead of --agent-port\r\n%s\r\n' % (opt[1], helpMessage))
        sys.exit(-1)
    elif opt[0] == '--v2c-arch':
        v2cArch = True
    elif opt[0] == '--v3-only':
        v3Only = True
    elif opt[0] == '--v3-user':
        v3Users.append(opt[1])
    elif opt[0] == '--v3-auth-key':
        v3AuthKeys[v3Users[-1]] = opt[1]
    elif opt[0] == '--v3-auth-proto':
        v3AuthProtos[v3Users[-1]] = opt[1].upper()
        if v3AuthProtos[v3Users[-1]] not in authProtocols:
            sys.stderr.write('ERROR: bad v3 auth protocol %s\r\n%s\r\n' % (v3AuthProtos[v3Users[-1]], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--v3-priv-key':
        v3PrivKeys[v3Users[-1]] = opt[1]
    elif opt[0] == '--v3-priv-proto':
        v3PrivProtos[v3Users[-1]] = opt[1].upper()
        if v3PrivProtos[v3Users[-1]] not in privProtocols:
            sys.stderr.write('ERROR: bad v3 privacy protocol %s\r\n%s\r\n' % (v3PrivProtos[v3Users[-1]], helpMessage))
            sys.exit(-1)

for v3User in v3Users:
    if v3User in v3AuthKeys:
        if v3User not in v3AuthProtos:
            v3AuthProtos[v3User] = 'MD5'
    else:
        v3AuthKeys[v3User] = None
        v3AuthProtos[v3User] = 'NONE'
    if v3User in v3PrivKeys:
        if v3User not in v3PrivProtos:
            v3PrivProtos[v3User] = 'DES'
    else:
        v3PrivKeys[v3User] = None
        v3PrivProtos[v3User] = 'NONE'
    if authProtocols[v3AuthProtos[v3User]] == config.usmNoAuthProtocol and \
            privProtocols[v3PrivProtos[v3User]] != config.usmNoPrivProtocol:
        sys.stderr.write('ERROR: privacy impossible without authentication\r for USM user %s\n%s\r\n', (v3User, helpMessage))
        sys.exit(-1)

if not v3Users:
    v3Users = [ 'simulator' ]
    v3AuthKeys[v3Users[0]] = 'auctoritas'
    v3AuthProtos[v3Users[0]] = 'MD5'
    v3PrivKeys[v3Users[0]] = 'privatus'
    v3PrivProtos[v3Users[0]] = 'DES'

if not agentUDPv4Endpoints and \
        not agentUDPv6Endpoints and \
        not agentUNIXEndpoints:
    sys.stderr.write('ERROR: agent endpoint address(es) not specified\r\n%s\r\n' % helpMessage)
    sys.exit(-1)

try:
    daemon.dropPrivileges(procUser, procGroup)
except:
    sys.stderr.write('ERROR: cant drop priveleges: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if not foregroundFlag:
    try:
        daemon.daemonize(pidFile)
    except:
        sys.stderr.write('ERROR: cant daemonize process: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
        sys.exit(-1)

for variationModulesDir in confdir.variation:
    log.msg('Scanning "%s" directory for variation modules...' % variationModulesDir)
    if not os.path.exists(variationModulesDir):
        log.msg('Directory %s does not exist' % variationModulesDir)
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
            _toLoad.append((modName, ''))

        mod = variationModulesDir + os.path.sep + dFile

        for alias, args in _toLoad:
            if alias in variationModules:
                log.msg('WARNING: ignoring duplicate module %s at %s' %  (alias, mod))
                continue

            ctx = { 'path': mod,
                    'alias': alias,
                    'args': args,
                    'moduleContext': {} }

            try:
                if sys.version_info[0] > 2:
                    exec(compile(open(mod).read(), mod, 'exec'), ctx)
                else:
                    execfile(mod, ctx)
            except Exception:
                log.msg('Variation module %s execution failure: %s' %  (mod, sys.exc_info()[1]))
                sys.exit(-1)
            else:
                # moduleContext, agentContext, recordContext
                variationModules[alias] = ctx, {}, {}

    log.msg('A total of %s modules found in %s' % (len(variationModules), variationModulesDir))

if variationModulesOptions:
    log.msg('WARNING: unused options for variation modules: %s' %  ', '.join(variationModulesOptions.keys()))

if not os.path.exists(confdir.cache):
    try:
        os.makedirs(confdir.cache)
    except OSError:
        log.msg('ERROR: failed to create cache directory %s: %s' % (confdir.cache, sys.exc_info()[1]))
        sys.exit(-1)
    else:
        log.msg('Cache directory %s created' % confdir.cache)


# Basic SNMP engine configuration

if v2cArch:
    contexts = { univ.OctetString('index'): dataIndexInstrumController }
else:
    snmpEngine = engine.SnmpEngine()

    config.addContext(snmpEngine, '')

    snmpContext = context.SnmpContext(snmpEngine)
        
    for v3User in v3Users:
        config.addV3User(
            snmpEngine,
            v3User,
            authProtocols[v3AuthProtos[v3User]], v3AuthKeys[v3User],
            privProtocols[v3PrivProtos[v3User]], v3PrivKeys[v3User]
        )

if variationModules:
    log.msg('Initializing variation modules...')
    for name, modulesContexts in variationModules.items():
        body = modulesContexts[0]
        for x in ('init', 'variate', 'shutdown'):
            if x not in body:
                log.msg('ERROR: missing %s handler in %s!' % (x, name))
                sys.exit(-1)
        try:
            body['init'](not v2cArch and snmpEngine or None,
                         options=body['args'],
                         mode='variating')
        except Exception:
            log.msg('Module %s load FAILED: %s' % (name,sys.exc_info()[1]))
        else:
            log.msg('Modile %s loaded OK' % name)

# Build pysnmp Managed Objects base from data files information

_mibInstrums = {}
_dataFiles = {}

for dataDir in confdir.data:
    log.msg('Scanning "%s" directory for %s data files...' % (dataDir, ','.join([' *%s%s' % (os.path.extsep, x.ext) for x in recordSet.values()]))
    )
    if not os.path.exists(dataDir):
        log.msg('Directory %s does not exist' % dataDir)
        continue
    log.msg('%s' % ('='*66,))
    for fullPath, textParser, communityName in getDataFiles(dataDir):
        if communityName in _dataFiles:
            log.msg('WARNING: ignoring duplicate Community/ContextName "%s" for data file %s (%s already loaded)' % (communityName, fullPath, _dataFiles[communityName]))
            continue
        elif fullPath in _mibInstrums:
            mibInstrum = _mibInstrums[fullPath]
            log.msg('Configuring *shared* %s' % (mibInstrum,))
        else:
            dataFile = DataFile(fullPath, textParser).indexText(forceIndexBuild)
            mibInstrum = mibInstrumControllerSet[dataFile.layout](dataFile)

            _mibInstrums[fullPath] = mibInstrum
            _dataFiles[communityName] = fullPath

            log.msg('Configuring %s' % (mibInstrum,))

        log.msg('SNMPv1/2c community name: %s' % (communityName,))

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
                 
            log.msg('SNMPv3 context name: %s' % (contextName,))
        
        log.msg('%s' % ('-+' * 33,))
        
del _mibInstrums
del _dataFiles

if v2cArch:
    def getBulkHandler(reqVarBinds, nonRepeaters, maxRepetitions, readNextVars):
        N = min(int(nonRepeaters), len(reqVarBinds))
        M = int(maxRepetitions)
        R = max(len(reqVarBinds)-N, 0)
        if R: M = min(M, 100/R)  # maxVarBinds

        if N:
            rspVarBinds = readNextVars(reqVarBinds[:N])
        else:
            rspVarBinds = []

        varBinds = reqVarBinds[-R:]
        while M and R:
            rspVarBinds.extend(
                readNextVars(varBinds)
            )
            varBinds = rspVarBinds[-R:]
            M = M - 1

        return rspVarBinds
 
    def commandResponderCbFun(transportDispatcher, transportDomain,
                              transportAddress, wholeMsg):
        while wholeMsg:
            msgVer = api.decodeMessageVersion(wholeMsg)
            if msgVer in api.protoModules:
                pMod = api.protoModules[msgVer]
            else:
                log.msg('Unsupported SNMP version %s' % (msgVer,))
                return
            reqMsg, wholeMsg = decoder.decode(
                wholeMsg, asn1Spec=pMod.Message(),
                )

            communityName = reqMsg.getComponentByPosition(1)
            for candidate in probeContext(transportDomain, transportAddress, communityName):
                if candidate in contexts:
                    log.msg('Using %s selected by candidate %s; transport ID %s, source address %s, community name "%s"' % (contexts[candidate], candidate, univ.ObjectIdentifier(transportDomain), transportAddress[0], communityName))
                    communityName = candidate
                    break
            else:
                log.msg('No data file selected for transport ID %s, source address %s, community name "%s"' % (univ.ObjectIdentifier(transportDomain), transportAddress[0], communityName))
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
                    log.msg('GETBULK over SNMPv1 from %s:%s' % (
                        transportDomain, transportAddress
                        ))
                    return wholeMsg
                backendFun = lambda varBinds: getBulkHandler(varBinds,
                    pMod.apiBulkPDU.getNonRepeaters(reqPDU),
                    pMod.apiBulkPDU.getMaxRepetitions(reqPDU),
                    contexts[communityName].readNextVars)
            else:
                log.msg('Unsuppored PDU type %s from %s:%s' % (
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
   
    transportDispatcher = AsynsockDispatcher()
    for idx in range(len(agentUDPv4Endpoints)):
        transportDispatcher.registerTransport(
                udp.domainName + (idx,), agentUDPv4Endpoints[idx][0]
            )
        log.msg('Listening at UDP/IPv4 endpoint %s, transport ID %s' % (agentUDPv4Endpoints[idx][1], '.'.join([str(x) for x in udp.domainName + (idx,)]),))
    for idx in range(len(agentUDPv6Endpoints)):
        transportDispatcher.registerTransport(
                udp6.domainName + (idx,), agentUDPv6Endpoints[idx][0]
            )
        log.msg('Listening at UDP/IPv6 endpoint %s, transport ID %s' % (agentUDPv6Endpoints[idx][1], '.'.join([str(x) for x in udp6.domainName + (idx,)]),))
    for idx in range(len(agentUNIXEndpoints)):
        transportDispatcher.registerTransport(
                unix.domainName + (idx,), agentUNIXEndpoints[idx][0]
            )
        log.msg('Listening at UNIX domain endpoint %s, transport ID %s' % (agentUNIXEndpoints[idx][1], '.'.join([str(x) for x in unix.domainName + (idx,)])))
    transportDispatcher.registerRecvCbFun(commandResponderCbFun)
else:
    for v3User in v3Users:
        log.msg('%s' % ('-'*66,))
        log.msg('SNMPv3 USM SecurityName: %s' % v3User)
        if authProtocols[v3AuthProtos[v3User]] != config.usmNoAuthProtocol:
            log.msg('SNMPv3 USM authentication key: %s, authentication protocol: %s' % (v3AuthKeys[v3User], v3AuthProtos[v3User]))
            if privProtocols[v3PrivProtos[v3User]] != config.usmNoPrivProtocol:
                log.msg('SNMPv3 USM encryption (privacy) key: %s, encryption protocol: %s' % (v3PrivKeys[v3User], v3PrivProtos[v3User]))

    # Configure access to data index

    config.addV1System(snmpEngine, 'index',
                       'index', contextName='index')

    snmpContext.registerContextName(
        'index', dataIndexInstrumController
        )

    # Configure socket server

    for idx in range(len(agentUDPv4Endpoints)):
        config.addSocketTransport(
            snmpEngine,
            udp.domainName + (idx,), agentUDPv4Endpoints[idx][0]
        )
        log.msg('Listening at UDP/IPv4 endpoint %s, transport ID %s' % (agentUDPv4Endpoints[idx][1], '.'.join([str(x) for x in udp.domainName + (idx,)]),))
    for idx in range(len(agentUDPv6Endpoints)):
        config.addSocketTransport(
            snmpEngine,
            udp6.domainName + (idx,), agentUDPv6Endpoints[idx][0]
        )
        log.msg('Listening at UDP/IPv6 endpoint %s, transport ID %s' % (agentUDPv6Endpoints[idx][1], '.'.join([str(x) for x in udp6.domainName + (idx,)]),))
    for idx in range(len(agentUNIXEndpoints)):
        config.addSocketTransport(
            snmpEngine,
            unix.domainName + (idx,), agentUNIXEndpoints[idx][0]
        )
        log.msg('Listening at UNIX domain endpoint %s, transport ID %s' % (agentUNIXEndpoints[idx][1], '.'.join([str(x) for x in unix.domainName + (idx,)])))

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
    log.msg('Shutting down process...')
except Exception:
    exc_info = sys.exc_info()

if variationModules:
    log.msg('Shutting down variation modules:')
    for name, contexts in variationModules.items():
        body = contexts[0]
        try:
            body['shutdown'](not v2cArch and snmpEngine or None,
                             options=body['args'], mode='variation')
        except Exception:
            log.msg('Module %s shutdown FAILED: %s' % (name, sys.exc_info()[1]))
        else:
            log.msg('Module %s shutdown OK' % name)

transportDispatcher.closeDispatcher()

log.msg('Process terminated')

if exc_info:
    for line in traceback.format_exception(*exc_info):
        log.msg(line.replace('\n', ';'))
