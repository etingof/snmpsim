#!/usr/bin/env python
#
# SNMP Simulator MIB to data file converter
#
# Written by Ilya Etingof <ilya@glas.net>, 2011-2013
#
import getopt
import sys
import os
import time
import socket
import struct
import traceback
try:
    import pcap
except ImportError:
    sys.stderr.write("""Install pylibpcap module and try again!
""")
    sys.exit(-1)
from pyasn1.codec.ber import decoder
from pyasn1.error import PyAsn1Error
from pysnmp.proto import api
from pysnmp.carrier.asynsock.dgram import udp
from snmpsim.record import snmprec
from snmpsim import confdir, error, log

# Defaults
verboseFlag = True
startOID = stopOID = None
dataDir = '.'
outputFile = sys.stderr
listenInterface = captureFile = None
packetFilter = 'src port 161'

endpoints = {}
contexts = {}

stats = {
  'UDP packets': 0,
  'IP packets': 0,
  'bad SNMP packets': 0,
  'SNMP errors': 0,
  'SNMP agents seen': 0,
  'SNMP contexts seen': 0,
  'SNMP snapshots taken': 0,
  'SNMP Response PDUs seen': 0,
  'SNMP OIDs seen': 0
}

helpMessage = """Usage: %s [--help]
    [--version]
    [--quiet]
    [--logging-method=<stdout|stderr|syslog|file>[:args>]]
    [--start-oid=<OID>] [--stop-oid=<OID>]
    [--data-dir=<directory>]
    [--capture-file=<filename.pcap>]
    [--listen-interface=<device>]
    [--packet-filter=<ruleset>]""" % sys.argv[0] 

log.setLogger('pcap2dev', 'stdout')

try:
    opts, params = getopt.getopt(sys.argv[1:], 'hv',
        ['help', 'version', 'quiet', 'logging-method=', 'start-oid=', 'stop-oid=', 'data-dir=', 'capture-file=', 'listen-interface=', 'packet-filter=']
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
  Snoops network traffic for SNMP responses, builds SNMP Simulator
  data files.
  Can read capture files or listen live network interface.
Documentation:
  http://snmpsim.sourceforge.net/
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
    if opt[0] == '--quiet':
        verboseFlag = False
    elif opt[0] == '--logging-method':
        try:
            log.setLogger('snmprec', *opt[1].split(':'))
        except error.SnmpsimError:
            sys.stderr.write('%s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
            sys.exit(-1)
    elif opt[0] == '--data-dir':
        dataDir = opt[1]
    elif opt[0] == '--listen-interface':
        listenInterface = opt[1]
    elif opt[0] == '--capture-file':
        captureFile = opt[1]
    elif opt[0] == '--packet-filter':
        packetFilter = opt[1]

if params:
    sys.stderr.write('ERROR: extra arguments supplied %s\r\n%s\r\n' % (params, helpMessage))
    sys.exit(-1)    

pcapObj = pcap.pcapObject()

if listenInterface:
    if verboseFlag:
        log.msg('Openning interface %s' % opt[1])
    try:
        pcapObj.open_live(listenInterface, 1600, 0, 100)
    except:
        log.msg('Error openning interface %s for snooping: %s' % (listenInteface, sys.exc_info()[1]))
        sys.exit(-1)
elif captureFile:
    if verboseFlag:
        log.msg('Openning capture file %s' % captureFile)
    try:
        pcapObj.open_offline(captureFile)
    except:
        log.msg('Error openning capture file %s for reading: %s' % (captureFile, sys.exc_info()[1]))
        sys.exit(-1)
else: 
    sys.stderr.write('ERROR: no capture file or live interface specified\r\n%s\r\n' % helpMessage)
    sys.exit(-1)

if packetFilter:
    if verboseFlag:
        log.msg('Applying packet filter \"%s\"' % packetFilter)
    pcapObj.setfilter(packetFilter, 0, 0)

def parseUdpPacket(s):
    d={}
    d['version']=(ord(s[0]) & 0xf0) >> 4
    d['header_len']=ord(s[0]) & 0x0f
    d['tos']=ord(s[1])
    d['total_len']=socket.ntohs(struct.unpack('H',s[2:4])[0])
    d['id']=socket.ntohs(struct.unpack('H',s[4:6])[0])
    d['flags']=(ord(s[6]) & 0xe0) >> 5
    d['fragment_offset']=socket.ntohs(struct.unpack('H',s[6:8])[0] & 0x1f)
    d['ttl']=ord(s[8])
    d['protocol']=ord(s[9])
    d['checksum']=socket.ntohs(struct.unpack('H',s[10:12])[0])
    d['source_address']=pcap.ntoa(struct.unpack('i',s[12:16])[0])
    d['destination_address']=pcap.ntoa(struct.unpack('i',s[16:20])[0])
    if d['header_len']>5:
        d['options']=s[20:4*(d['header_len']-5)]
    else:
        d['options']=None
    s = s[4*d['header_len']:]
    if d['protocol'] == 17:
        d['source_port'] = socket.ntohs(struct.unpack('H',s[0:2])[0])
        d['destination_port'] = socket.ntohs(struct.unpack('H',s[2:4])[0])
        s = s[8:]
        stats['UDP packets'] +=1
    d['data'] = s
    stats['IP packets'] +=1
    return d

def handleSnmpMessage(d, t):
    msgVer = api.decodeMessageVersion(d['data'])
    if msgVer in api.protoModules:
        pMod = api.protoModules[msgVer]
    else:
        stats['bad SNMP packets'] +=1
        return
    try:
        rspMsg, wholeMsg = decoder.decode(
            d['data'], asn1Spec=pMod.Message(),
        )
    except PyAsn1Error:
        stats['bad SNMP packets'] +=1
        return
    if rspMsg['data'].getName() == 'response':
        rspPDU = pMod.apiMessage.getPDU(rspMsg)
        errorStatus = pMod.apiPDU.getErrorStatus(rspPDU)
        if errorStatus:
            stats['SNMP errors'] +=1
        else:
            endpoint = d['source_address'], d['source_port']
            if endpoint not in endpoints:
                endpoints[endpoint] = udp.domainName + (len(endpoints),)
                stats['SNMP agents seen'] +=1
            context = '%s/%s' % (pMod.ObjectIdentifier(endpoints[endpoint]), pMod.apiMessage.getCommunity(rspMsg))
            if context not in contexts:
                contexts[context] = {}
                stats['SNMP contexts seen'] +=1
            context = '%s/%s' % (pMod.ObjectIdentifier(endpoints[endpoint]), pMod.apiMessage.getCommunity(rspMsg))

            stats['SNMP Response PDUs seen'] += 1

            for oid, value in pMod.apiPDU.getVarBinds(rspPDU):
                if oid in contexts[context]:
                    if value != contexts[context][oid]:
                        stats['SNMP snapshots taken'] +=1
                else:
                    contexts[context][oid] = {}
                contexts[context][oid][t] = value
                stats['SNMP OIDs seen'] += 1
 
def handlePacket(pktlen, data, timestamp):
    if not data:
        return
    elif data[12:14]=='\x08\x00':
        handleSnmpMessage(parseUdpPacket(data[14:]), timestamp)

exc_info = None

try:
    while 1:
        pcapObj.loop(1, handlePacket)

except KeyboardInterrupt:
    log.msg('Shutting down process...')

except Exception:
    exc_info = sys.exc_info()

for context in contexts:
    filename = os.path.join(dataDir, context + os.path.extsep + snmprec.SnmprecRecord.ext)
    if verboseFlag:
        log.msg('Creating simulation context %s at %s' % (context, filename))
    try:
        os.mkdir(os.path.dirname(filename))
    except OSError:
        pass
    try:
        outputFile = open(filename, 'wb')
    except IOError:
        log.msg('ERROR: writing %s: %s' % (filename, sys.exc_info()[1]))
        sys.exit(-1)

    oids = list(contexts[context].keys())
    oids.sort()
    for oid in oids:
        outputFile.write(
            snmprec.SnmprecRecord().format(oid, contexts[context][oid].values()[0])
        )
    outputFile.close()

log.msg("""Statistics:
    packets read: %s
    packets dropped %s
    packets dropped by interface %s""" % pcapObj.stats())

log.msg('    '+'    '.join([ '%s: %s\r\n' % kv for kv in stats.items() ]))

if exc_info:
    for line in traceback.format_exception(*exc_info):
        log.msg(line.replace('\n', ';'))
