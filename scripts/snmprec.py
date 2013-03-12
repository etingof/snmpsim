#
# SNMP Snapshot Data Recorder
#
# Written by Ilya Etingof <ilya@glas.net>, 2010-2013
#

import getopt
import time
import sys
from pyasn1.type import univ
from pysnmp.proto import rfc1902, rfc1905
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
from snmpsim import __version__
from snmpsim.grammar import snmprec

# Defaults
quietFlag = False
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

helpMessage = 'Usage: %s [--help] [--debug=<category>] [--quiet] [--version=<1|2c|3>] [--community=<string>] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-auth-proto=<%s>] [--v3-priv-proto=<%s>] [--context=<string>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--start-oid=<OID>] [--stop-oid=<OID>] [--output-file=<filename>]' % (sys.argv[0], '|'.join([ x for x in authProtocols if x != 'NONE' ]), '|'.join([ x for x in privProtocols if x != 'NONE' ]))

try:
    opts, params = getopt.getopt(sys.argv[1:], 'h',
        ['help', 'debug=', 'quiet', 'v1', 'v2c', 'v3', 'version=', 'community=', 'v3-user=', 'v3-auth-key=', 'v3-priv-key=', 'v3-auth-proto=', 'v3-priv-proto=', 'context=', 'agent-address=', 'agent-port=', 'agent-udpv4-endpoint=', 'agent-udpv6-endpoint=', 'agent-unix-endpoint=', 'start-oid=', 'stop-oid=', 'output-file=']
        )
except Exception:
    sys.stdout.write('getopt error: %s\r\n' % sys.exc_info()[1])
    sys.stdout.write(helpMessage + '\r\n')
    sys.exit(-1)

if params:
    sys.stdout.write('extra arguments supplied %s\r\n' % params)
    sys.stdout.write(helpMessage + '\r\n')
    sys.exit(-1)

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stdout.write('SNMP Simulator version %s, written by Ilya Etingof <ilya@glas.net>\r\nSoftware documentation and support at http://snmpsim.sf.net\r\n%s\r\n' % (__version__, helpMessage))
        sys.exit(-1)
    elif opt[0] == '--debug':
        debug.setLogger(debug.Debug(opt[1]))
    elif opt[0] == '--quiet':
        quietFlag = True
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
            sys.stdout.write('unknown SNMP version %s\r\n' % opt[1])
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
            sys.stdout.write('bad v3 auth protocol %s\r\n' % v3AuthProto)
            sys.exit(-1)
    elif opt[0] == '--v3-priv-key':
        v3PrivKey = opt[1]
    elif opt[0] == '--v3-priv-proto':
        v3PrivProto = opt[1].upper()
        if v3PrivProto not in privProtocols:
            sys.stdout.write('bad v3 privacy protocol %s\r\n' % v3PrivProto)
            sys.exit(-1)
    elif opt[0] == '--context':
        v3Context = opt[1]
    elif opt[0] == '--agent-address':
        agentUDPv4Address = (opt[1], agentUDPv4Address[1])
    elif opt[0] == '--agent-port':
        agentUDPv4Address = (agentUDPv4Address[0], int(opt[1]))
    elif opt[0] == '--agent-udpv4-endpoint':
        f = lambda h,p=161: (h, int(p))
        try:
            agentUDPv4Endpoint = f(*opt[1].split(':'))
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
                agentUDPv6Endpoint = h[1:], int(p)
            except:
                sys.stdout.write('improper IPv6/UDP endpoint %s\r\n' % opt[1])
                sys.exit(-1)
        elif opt[1][0] == '[' and opt[1][-1] == ']':
            agentUDPv6Endpoint = opt[1][1:-1], 161
        else:
            agentUDPv6Endpoint = opt[1], 161
    elif opt[0] == '--agent-unix-endpoint':
        if not unix:
            sys.stdout.write('This system does not support UNIX domain sockets\r\n')
            sys.exit(-1)
        agentUNIXEndpoint = opt[1]
    elif opt[0] == '--start-oid':
        startOID = univ.ObjectIdentifier(opt[1])
    elif opt[0] == '--stop-oid':
        stopOID = univ.ObjectIdentifier(opt[1])
    elif opt[0] == '--output-file':
        outputFile = open(opt[1], 'w')

# Catch missing params

if not agentUDPv4Endpoint and not agentUDPv6Endpoint and not agentUNIXEndpoint:
    if agentUDPv4Address[0] is None:
        sys.stdout.write('ERROR: agent address endpoint not given\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    else:
        agentUDPv4Endpoint = agentUDPv4Address

if snmpVersion == 3:
    if v3User is None:
        sys.stdout.write('--v3-user is missing\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    if v3PrivKey and not v3AuthKey:
        sys.stdout.write('--v3-auth-key is missing\r\n%s\r\n' % helpMessage)
        sys.exit(-1)
    if authProtocols[v3AuthProto] == config.usmNoAuthProtocol:
        if v3AuthKey is not None:
            v3AuthProto = 'MD5'
    else:
        if v3AuthKey is None:
            sys.stdout.write('--v3-auth-key is missing\r\n%s\r\n' % helpMessage)
            sys.exit(-1)
    if privProtocols[v3PrivProto] == config.usmNoPrivProtocol:
        if v3PrivKey is not None:
            v3PrivProto = 'DES'
    else:
        if v3PrivKey is None:
            sys.stdout.write('--v3-priv-key is missing\r\n%s\r\n' % helpMessage)
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
    if not quietFlag:
        sys.stdout.write('SNMP version 3\r\nContext name: %s\r\nUser: %s\r\nSecurity level: %s\r\nAuthentication key/protocol: %s/%s\r\nEncryption (privacy) key/protocol: %s/%s\r\n' % (v3Context == '' and '\'\'' or v3Context, v3User, secLevel, v3AuthKey is None and '<NONE>' or v3AuthKey, v3AuthProto, v3PrivKey is None and '<NONE>' or v3PrivKey, v3PrivProto))
else:
    v3User = 'agt'
    secLevel = 'noAuthNoPriv'
    config.addV1System(
        snmpEngine, v3User, snmpCommunity
    )
    if not quietFlag:
        sys.stdout.write('SNMP version %s\r\nCommunity name: %s\r\n' % (snmpVersion == 0 and '1' or '2c', snmpCommunity))

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
    if not quietFlag:
        sys.stdout.write('Querying UDP/IPv6 agent at [%s]:%s\r\n' % agentUDPv6Endpoint)
elif agentUNIXEndpoint:
    config.addSocketTransport(
        snmpEngine,
        unix.domainName,
        unix.UnixSocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine, 'tgt', unix.domainName, agentUNIXEndpoint, 'pms'
    )
    if not quietFlag:
        sys.stdout.write('Querying UNIX named pipe agent at %s\r\n' % agentUNIXEndpoint)
elif agentUDPv4Endpoint:
    config.addSocketTransport(
        snmpEngine,
        udp.domainName,
        udp.UdpSocketTransport().openClientMode()
    )
    config.addTargetAddr(
        snmpEngine, 'tgt', udp.domainName, agentUDPv4Endpoint, 'pms'
    )
    if not quietFlag:
        sys.stdout.write('Querying UDP/IPv4 agent at %s:%s\r\n' % agentUDPv4Endpoint)

# Data file builder

dataFileHandler = snmprec.SnmprecGrammar()

# SNMP worker

def cbFun(sendRequestHandle, errorIndication, errorStatus, errorIndex,
          varBindTable, cbCtx):
    if errorIndication and errorIndication != 'oidNotIncreasing':
        sys.stdout.write('%s\r\n' % errorIndication)
        return
    # SNMPv1 response may contain noSuchName error *and* SNMPv2c exception,
    # so we ignore noSuchName error here
    if errorStatus and errorStatus != 2:
        sys.stdout.write('%s\r\n' % errorStatus.prettyPrint())
        return
    for varBindRow in varBindTable:
        for oid, val in varBindRow:
            if val is None or val.tagSet in (rfc1905.NoSuchObject.tagSet,
                                             rfc1905.NoSuchInstance.tagSet,
                                             rfc1905.EndOfMibView.tagSet):
                continue
            outputFile.write(dataFileHandler.build(oid, val))
            cbCtx['count'] = cbCtx['count'] + 1
            if not quietFlag:
                sys.stdout.write('OIDs dumped: %s\r' % cbCtx['count']),
                sys.stdout.flush()
    for oid, val in varBindTable[-1]:
        if stopOID and oid >= stopOID:
            return # stop on out of range condition
        if val is not None:
            break
    else:
        return # stop on end-of-table
    return 1 # continue walking

cmdGen = cmdgen.NextCommandGenerator()

cbCtx = {
    'count': 0
    }

cmdGen.sendReq(
    snmpEngine, 'tgt', ((startOID, None),), cbFun, cbCtx, contextName=v3Context
    )

t = time.time()

# Python 2.4 does not support the "finally" clause

exc_info = None

try:
    snmpEngine.transportDispatcher.runDispatcher()
except KeyboardInterrupt:
    if not quietFlag:
        sys.stdout.write('Process terminated\r\n')
except Exception:
    exc_info = sys.exc_info()

snmpEngine.transportDispatcher.closeDispatcher()

t = time.time() - t

if not quietFlag:
    sys.stdout.write(
        'OIDs dumped: %s, elapsed: %.2f sec, rate: %.2f OIDs/sec\r\n' % \
        (cbCtx['count'], t, t and cbCtx['count']//t or 0)
        )

if exc_info:
    e = exc_info[0](exc_info[1])
    e.__traceback__ = exc_info[2]
    raise e
