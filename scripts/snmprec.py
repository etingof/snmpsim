#!/usr/bin/env python
#
# SNMP Snapshot Data Recorder
#
# Written by Ilya Etingof <ilya@glas.net>, 2010-2013
#

import getopt
import time
import sys
import os
import socket
import traceback
from pyasn1.type import univ
from pysnmp.proto import rfc1905
from pysnmp.entity import engine, config
from pysnmp.carrier.asynsock.dgram import udp
try:
    from pysnmp.carrier.asynsock.dgram import udp6
except ImportError:
    udp6 = None
try:
    from pysnmp.carrier.asynsock.dgram import unix
except ImportError:
    unix = None
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp import debug
from snmpsim.record import snmprec
from snmpsim import confdir, error, log

# Defaults
getBulkFlag = False
getBulkRepetitions = 25
snmpVersion = 1
snmpCommunity = 'public'
v3User = None
v3AuthKey = None
v3PrivKey = None
v3AuthProto = 'NONE'
v3PrivProto = 'NONE'
v3Context = ''
agentUDPv4Address = (None, 161)  # obsolete
agentUDPv4Endpoint = None
agentUDPv6Endpoint = None
agentUNIXEndpoint = None
startOID = univ.ObjectIdentifier('1.3.6')
stopOID = None
outputFile = sys.stderr
variationModuleOptions = ""
variationModuleName = variationModule = None

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

helpMessage = """\
Usage: %s [--help]
    [--version]
    [--debug=<%s>]
    [--logging-method=<stdout|stderr|syslog|file>[:args>]]
    [--version=<1|2c|3>]
    [--community=<string>]
    [--v3-user=<username>]
    [--v3-auth-key=<key>]
    [--v3-auth-proto=<%s>]
    [--v3-priv-key=<key>]
    [--v3-priv-proto=<%s>]
    [--context=<string>]
    [--use-getbulk]
    [--getbulk-repetitions=<number>]
    [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>]
    [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>]
    [--agent-unix-endpoint=</path/to/named/pipe>]
    [--start-oid=<OID>] [--stop-oid=<OID>]
    [--output-file=<filename>]
    [--variation-modules-dir=<dir>]
    [--variation-module=<module>]
    [--variation-module-options=<args>]""" % (
        sys.argv[0],
        '|'.join([ x for x in debug.flagMap.keys() if x != 'mibview' ]),
        '|'.join([ x for x in authProtocols if x != 'NONE' ]),
        '|'.join([ x for x in privProtocols if x != 'NONE' ])
    )

log.setLogger('snmprec', 'stdout')

try:
    opts, params = getopt.getopt(sys.argv[1:], 'hv',
        ['help', 'version', 'debug=', 'logging-method=', 'quiet', 'v1', 'v2c', 'v3', 'version=', 'community=', 'v3-user=', 'v3-auth-key=', 'v3-priv-key=', 'v3-auth-proto=', 'v3-priv-proto=', 'context=', 'use-getbulk', 'getbulk-repetitions=', 'agent-address=', 'agent-port=', 'agent-udpv4-endpoint=', 'agent-udpv6-endpoint=', 'agent-unix-endpoint=', 'start-oid=', 'stop-oid=', 'output-file=', 'variation-modules-dir=', 'variation-module=', 'variation-module-options=']
        )
except Exception:
    sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if params:
    sys.stderr.write('ERROR: extra arguments supplied %s\r\n%s\r\n' % (params, helpMessage))
    sys.exit(-1)

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  SNMP Agents Recording tool. Queries specified Agent, stores response
  data in data files for subsequent playback by SNMP Simulation tool.
  Can store a series of recordings for a more dynamic playback.
Documentation:
  http://snmpsim.sourceforge.net/snapshotting.html
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
    elif opt[0] == '--logging-method':
        try:
            log.setLogger('snmprec', *opt[1].split(':'))
        except error.SnmpsimError:
            sys.stderr.write('%s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--quiet':
        log.setLogger('snmprec', 'null') 
    elif opt[0] == '--v1':
        snmpVersion = 0
    elif opt[0] == '--v2c':
        snmpVersion = 1
    elif opt[0] == '--v3':
        snmpVersion = 3
    elif opt[0] == '--version':
        if opt[1] in ('1', 'v1'):
            snmpVersion = 0
        elif opt[1] in ('2', '2c', 'v2c'):
            snmpVersion = 1
        elif opt[1] in ('3', 'v3'):
            snmpVersion = 3
        else:
            sys.stderr.write('ERROR: unknown SNMP version %s\r\n%s\r\n' % (opt[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--community':
        snmpCommunity = opt[1]
    elif opt[0] == '--v3-user':
        v3User = opt[1]
    elif opt[0] == '--v3-auth-key':
        v3AuthKey = opt[1]
    elif opt[0] == '--v3-auth-proto':
        v3AuthProto = opt[1].upper()
        if v3AuthProto not in authProtocols:
            sys.stderr.write('ERROR: bad v3 auth protocol %s\r\n%s\r\n' % (v3AuthProto, helpMessage))
            sys.exit(-1)
    elif opt[0] == '--v3-priv-key':
        v3PrivKey = opt[1]
    elif opt[0] == '--v3-priv-proto':
        v3PrivProto = opt[1].upper()
        if v3PrivProto not in privProtocols:
            sys.stderr.write('ERROR: bad v3 privacy protocol %s\r\n%s\r\n' % (v3PrivProto, helpMessage))
            sys.exit(-1)
    elif opt[0] == '--context':
        v3Context = opt[1]
    elif opt[0] == '--use-getbulk':
        getBulkFlag = True
    elif opt[0] == '--getbulk-repetitions':
        getBulkRepetitions = int(opt[1])
    elif opt[0] == '--agent-address':
        agentUDPv4Address = (opt[1], agentUDPv4Address[1])
    elif opt[0] == '--agent-port':
        agentUDPv4Address = (agentUDPv4Address[0], int(opt[1]))
    elif opt[0] == '--agent-udpv4-endpoint':
        f = lambda h,p=161: (h, int(p))
        try:
            agentUDPv4Endpoint = f(*opt[1].split(':'))
        except:
            sys.stderr.write('ERROR: improper IPv4/UDP endpoint %s\r\n%s\r\n' % (opt[1], helpMessage))
            sys.exit(-1)
        try:
            agentUDPv4Endpoint = socket.getaddrinfo(agentUDPv4Endpoint[0], agentUDPv4Endpoint[1], socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)[0][4][:2]
        except socket.gaierror:
            sys.stderr.write('ERROR: unknown hostname %s\r\n%s\r\n' % (agentUDPv4Endpoint[0], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-udpv6-endpoint':
        if not udp6:
            sys.stderr.write('This system does not support UDP/IP6\r\n')
            sys.exit(-1)
        if opt[1].find(']:') != -1 and opt[1][0] == '[':
            h, p = opt[1].split(']:')
            try:
                agentUDPv6Endpoint = h[1:], int(p)
            except:
                sys.stderr.write('ERROR: improper IPv6/UDP endpoint %s\r\n%s\r\n' % (opt[1], helpMessage))
                sys.exit(-1)
        elif opt[1][0] == '[' and opt[1][-1] == ']':
            agentUDPv6Endpoint = opt[1][1:-1], 161
        else:
            agentUDPv6Endpoint = opt[1], 161
        try:
            agentUDPv6Endpoint = socket.getaddrinfo(agentUDPv6Endpoint[0], agentUDPv6Endpoint[1], socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)[0][4][:2]
        except socket.gaierror:
            sys.stderr.write('ERROR: unknown hostname %s\r\n%s\r\n' % (agentUDPv6Endpoint[0], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--agent-unix-endpoint':
        if not unix:
            sys.stderr.write('This system does not support UNIX domain sockets\r\n')
            sys.exit(-1)
        agentUNIXEndpoint = opt[1]
    elif opt[0] == '--start-oid':
        startOID = univ.ObjectIdentifier(opt[1])
    elif opt[0] == '--stop-oid':
        stopOID = univ.ObjectIdentifier(opt[1])
    elif opt[0] == '--output-file':
        outputFile = open(opt[1], 'wb')
    elif opt[0] == '--variation-modules-dir':
        confdir.variation.insert(0, opt[1])
    elif opt[0] == '--variation-module':
        variationModuleName = opt[1]
    elif opt[0] == '--variation-module-options':
        variationModuleOptions = opt[1]
 
# Catch missing params

if not agentUDPv4Endpoint and not agentUDPv6Endpoint and not agentUNIXEndpoint:
    if agentUDPv4Address[0] is None:
        sys.stderr.write('ERROR: agent endpoint address not specified\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    else:
        agentUDPv4Endpoint = agentUDPv4Address

if snmpVersion == 3:
    if v3User is None:
        sys.stderr.write('ERROR: --v3-user is missing\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    if v3PrivKey and not v3AuthKey:
        sys.stderr.write('ERROR: --v3-auth-key is missing\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    if authProtocols[v3AuthProto] == config.usmNoAuthProtocol:
        if v3AuthKey is not None:
            v3AuthProto = 'MD5'
    else:
        if v3AuthKey is None:
            sys.stderr.write('ERROR: --v3-auth-key is missing\r\n%s\r\n' % helpMessage)
            sys.exit(-1)
    if privProtocols[v3PrivProto] == config.usmNoPrivProtocol:
        if v3PrivKey is not None:
            v3PrivProto = 'DES'
    else:
        if v3PrivKey is None:
            sys.stderr.write('ERROR: --v3-priv-key is missing\r\n%s\r\n' % helpMessage)
            sys.exit(-1)
 
if getBulkFlag and not snmpVersion:
    log.msg('WARNING: will be using GETNEXT with SNMPv1!')
    getBulkFlag = False

# Attempt to reopen std output stream in binary mode
if outputFile is sys.stderr:
    if sys.version_info[0] > 2:
        outputFile = outputFile.buffer
    elif sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(outputFile.fileno(), os.O_BINARY)

# Load variation module

if variationModuleName:
    for variationModulesDir in confdir.variation:
        log.msg('Scanning "%s" directory for variation modules...' % variationModulesDir)
        if not os.path.exists(variationModulesDir):
            log.msg('Directory %s does not exist' % variationModulesDir)
            continue

        mod = os.path.join(variationModulesDir, variationModuleName + '.py')
        if not os.path.exists(mod):
            log.msg('Module %s not found' % mod)
            continue

        ctx = { 'path': mod, 'moduleContext': {} }

        try:
            if sys.version_info[0] > 2:
                exec(compile(open(mod).read(), mod, 'exec'), ctx)
            else:
                execfile(mod, ctx)
        except Exception:
            log.msg('Variation module %s execution failure: %s' %  (mod, sys.exc_info()[1]))
            sys.exit(-1)
        else:
            variationModule = ctx
            log.msg('Module %s loaded' % variationModuleName)
            break
    else:
        log.msg('ERROR: variation module %s not found' % variationModuleName)
        sys.exit(-1)
       
# SNMP configuration

snmpEngine = engine.SnmpEngine()

if snmpVersion == 3:
    if v3PrivKey is None and v3AuthKey is None:
        secLevel = 'noAuthNoPriv'
    elif v3PrivKey is None:
        secLevel = 'authNoPriv'
    else:
        secLevel = 'authPriv'
    config.addV3User(
        snmpEngine, v3User,
        authProtocols[v3AuthProto], v3AuthKey,
        privProtocols[v3PrivProto], v3PrivKey
        )
    log.msg('SNMP version 3, Context name: %s, SecurityName: %s, SecurityLevel: %s, Authentication key/protocol: %s/%s, Encryption (privacy) key/protocol: %s/%s' % (v3Context == '' and '\'\'' or v3Context, v3User, secLevel, v3AuthKey is None and '<NONE>' or v3AuthKey, v3AuthProto, v3PrivKey is None and '<NONE>' or v3PrivKey, v3PrivProto))
else:
    v3User = 'agt'
    secLevel = 'noAuthNoPriv'
    config.addV1System(
        snmpEngine, v3User, snmpCommunity
    )
    log.msg('SNMP version %s, Community name: %s' % (snmpVersion == 0 and '1' or '2c', snmpCommunity))

config.addTargetParams(snmpEngine, 'pms', v3User, secLevel, snmpVersion)

if agentUDPv6Endpoint:
    config.addSocketTransport(
        snmpEngine,
        udp6.domainName,
        udp6.Udp6SocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine, 'tgt', udp6.domainName, agentUDPv6Endpoint, 'pms'
    )
    log.msg('Querying UDP/IPv6 agent at [%s]:%s' % agentUDPv6Endpoint)
elif agentUNIXEndpoint:
    config.addSocketTransport(
        snmpEngine,
        unix.domainName,
        unix.UnixSocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine, 'tgt', unix.domainName, agentUNIXEndpoint, 'pms'
    )
    log.msg('Querying UNIX named pipe agent at %s' % agentUNIXEndpoint)
elif agentUDPv4Endpoint:
    config.addSocketTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpSocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine, 'tgt', udp.domainName, agentUDPv4Endpoint, 'pms'
    )
    log.msg('Querying UDP/IPv4 agent at %s:%s' % agentUDPv4Endpoint)

# Variation module initialization

if variationModule:
    log.msg('Initializing variation module...')
    for x in ('init', 'record', 'shutdown'):
        if x not in variationModule:
            log.msg('ERROR: missing %s handler at module %s' % (x, variationModuleName))
            sys.exit(-1)
    try:
        variationModule['init'](snmpEngine,
                                options=variationModuleOptions,
                                mode='recording',
                                startOID=startOID,
                                stopOID=stopOID)
    except Exception:
        log.msg('Module %s initialization FAILED: %s' % (variationModuleName, sys.exc_info()[1]))
    else:
        log.msg('Module %s initialization OK' % variationModuleName)

# Data file builder

class SnmprecRecord(snmprec.SnmprecRecord):
    def formatValue(self, oid, value, **context):
        textOid, textTag, textValue = snmprec.SnmprecRecord.formatValue(
            self, oid, value
        )

        # invoke variation module
        if context['variationModule']:
            plainOid, plainTag, plainValue = snmprec.SnmprecRecord.formatValue(
                self, oid, value, nohex=True
            )
            if plainTag != textTag:
                context['hextag'], context['hexvalue'] = textTag, textValue
            else:
                textTag, textValue = plainTag, plainValue

            textOid, textTag, textValue = context['variationModule']['record'](
                textOid, textTag, textValue, **context
            )

        elif 'stopFlag' in context and context['stopFlag']:
            raise error.NoDataNotification()

        return textOid, textTag, textValue

dataFileHandler = SnmprecRecord()

# SNMP worker

def cbFun(sendRequestHandle, errorIndication, errorStatus, errorIndex,
          varBindTable, cbCtx):
    if errorIndication and errorIndication != 'oidNotIncreasing':
        log.msg('SNMP Engine error: %s' % errorIndication)
        return
    # SNMPv1 response may contain noSuchName error *and* SNMPv2c exception,
    # so we ignore noSuchName error here
    if errorStatus and errorStatus != 2:
        log.msg('Remote SNMP error: %s' % errorStatus.prettyPrint())
        return

    stopFlag = False

    # Walk var-binds
    for varBindRow in varBindTable:
        for oid, val in varBindRow:
            # EOM
            if stopOID and oid >= stopOID:
                stopFlag = True # stop on out of range condition
            elif val is None or \
                val.tagSet in (rfc1905.NoSuchObject.tagSet,
                               rfc1905.NoSuchInstance.tagSet,
                               rfc1905.EndOfMibView.tagSet):
                stopFlag = True

            # Build .snmprec record

            context = {
                'origOid': oid,
                'origValue': val,
                'count': cbCtx['count'],
                'total': cbCtx['total'],
                'iteration': cbCtx['iteration'],
                'reqTime': cbCtx['reqTime'],
                'startOID': startOID,
                'stopOID': stopOID,
                'stopFlag': stopFlag,
                'variationModule': variationModule
            }

            try:
                line = dataFileHandler.format(oid, val, **context)
            except error.MoreDataNotification:
                cbCtx['total'] += cbCtx['count']
                cbCtx['count'] = 0
                cbCtx['iteration'] += 1
                # initiate another SNMP walk iteration
                if getBulkFlag:
                    cmdGen.sendReq(
                        snmpEngine, 'tgt', 0, getBulkRepetitions, 
                        ((startOID, None),), cbFun, cbCtx,
                        contextName=v3Context
                    )
                else:
                    cmdGen.sendReq(
                        snmpEngine, 'tgt', ((startOID, None),), cbFun, cbCtx,
                        contextName=v3Context
                    )
 
            except error.NoDataNotification:
                pass
            else:
                outputFile.write(line)

            cbCtx['count'] += 1

            if cbCtx['count'] % 100 == 0:
                log.msg('OIDs dumped: %s/%s' % (cbCtx['iteration'], cbCtx['count']))

    # Next request time
    cbCtx['reqTime'] = time.time()

    # Continue walking
    return not stopFlag

cbCtx = {
    'total': 0,
    'count': 0,
    'iteration': 0,
    'reqTime': time.time()
}

if getBulkFlag:
    cmdGen = cmdgen.BulkCommandGenerator()

    cmdGen.sendReq(
        snmpEngine, 'tgt', 0, getBulkRepetitions, ((startOID, None),), 
        cbFun, cbCtx, contextName=v3Context
    )
else:
    cmdGen = cmdgen.NextCommandGenerator()

    cmdGen.sendReq(
        snmpEngine, 'tgt', ((startOID, None),),
        cbFun, cbCtx, contextName=v3Context
    )

log.msg('Sending initial %s request....' % (getBulkFlag and 'GETBULK' or 'GETNEXT'))

t = time.time()

# Python 2.4 does not support the "finally" clause

exc_info = None

try:
    snmpEngine.transportDispatcher.runDispatcher()
except KeyboardInterrupt:
    log.msg('Shutting down process...')
except Exception:
    exc_info = sys.exc_info()

if variationModule:
    log.msg('Shutting down variation module %s...' % variationModuleName)
    try:
        variationModule['shutdown'](snmpEngine,
                                    options=variationModuleOptions,
                                    mode='recording')
    except Exception:
        log.msg('Variation module %s shutdown FAILED: %s' % (variationModuleName, sys.exc_info()[1]))
    else:
        log.msg('Variation module %s shutdown OK' % variationModuleName)

snmpEngine.transportDispatcher.closeDispatcher()

t = time.time() - t

cbCtx['total'] += cbCtx['count']

log.msg('OIDs dumped: %s, elapsed: %.2f sec, rate: %.2f OIDs/sec' % (cbCtx['total'], t, t and cbCtx['count']//t or 0))

if exc_info:
    for line in traceback.format_exception(*exc_info):
        log.msg(line.replace('\n', ';'))
