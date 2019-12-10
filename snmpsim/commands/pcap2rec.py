#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Simulator MIB to data file converter
#
import argparse
import bisect
import functools
import os
import socket
import struct
import sys
import time
import traceback

from pyasn1 import debug as pyasn1_debug
from pyasn1.codec.ber import decoder
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pysnmp import debug as pysnmp_debug
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.error import PySnmpError
from pysnmp.proto import api
from pysnmp.proto import rfc1905
from pysnmp.proto.rfc1902 import Bits
from pysnmp.proto.rfc1902 import Integer32
from pysnmp.proto.rfc1902 import OctetString
from pysnmp.proto.rfc1902 import Unsigned32
from pysnmp.smi import builder
from pysnmp.smi import compiler
from pysnmp.smi import rfc1902
from pysnmp.smi import view

from snmpsim import confdir
from snmpsim import error
from snmpsim import log
from snmpsim import utils
from snmpsim.record import dump
from snmpsim.record import mvc
from snmpsim.record import sap
from snmpsim.record import snmprec
from snmpsim.record import walk

pcap = utils.try_load('pcap')

RECORD_TYPES = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
    snmprec.SnmprecRecord.ext: snmprec.SnmprecRecord(),
    snmprec.CompressedSnmprecRecord.ext: snmprec.CompressedSnmprecRecord()
}

DESCRIPTION = (
    'Snoops network traffic for SNMP responses, builds SNMP Simulator '
    'data files. Can read capture files or listen live network interface.')


class SnmprecRecord(snmprec.SnmprecRecord):

    def formatValue(self, oid, value, **context):
        textOid, textTag, textValue = snmprec.SnmprecRecord.formatValue(
            self, oid, value)

        if context['variationModule']:
            plainOid, plainTag, plainValue = snmprec.SnmprecRecord.formatValue(
                self, oid, value, nohex=True)

            if plainTag != textTag:
                context['hextag'], context['hexvalue'] = textTag, textValue

            else:
                textTag, textValue = plainTag, plainValue

            handler = context['variationModule']['record']

            textOid, textTag, textValue = handler(
                textOid, textTag, textValue, **context)

        elif 'stopFlag' in context and context['stopFlag']:
            raise error.NoDataNotification()

        return textOid, textTag, textValue


def _parse_mib_object(arg, last=False):
    if '::' in arg:
        return rfc1902.ObjectIdentity(*arg.split('::', 1), last=last)

    else:
        return univ.ObjectIdentifier(arg)


def main():
    variation_module = None
    endpoints = {}
    contexts = {}

    stats = {
        'UDP packets': 0,
        'IP packets': 0,
        'bad packets': 0,
        'empty packets': 0,
        'unknown L2 protocol': 0,
        'SNMP errors': 0,
        'SNMP exceptions': 0,
        'agents seen': 0,
        'contexts seen': 0,
        'snapshots taken': 0,
        'Response PDUs seen': 0,
        'OIDs seen': 0
    }

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument(
        '-v', '--version', action='version',
        version=utils.TITLE)

    parser.add_argument(
        '--quiet', action='store_true',
        help='Do not print out informational messages')

    parser.add_argument(
        '--debug', choices=pysnmp_debug.flagMap,
        action='append', type=str, default=[],
        help='Enable one or more categories of SNMP debugging.')

    parser.add_argument(
        '--debug-asn1', choices=pyasn1_debug.FLAG_MAP,
        action='append', type=str, default=[],
        help='Enable one or more categories of ASN.1 debugging.')

    parser.add_argument(
        '--logging-method', type=lambda x: x.split(':'),
        metavar='=<%s[:args]>]' % '|'.join(log.METHODS_MAP),
        default='stderr', help='Logging method.')

    parser.add_argument(
        '--log-level', choices=log.LEVELS_MAP,
        type=str, default='info', help='Logging level.')

    parser.add_argument(
        '--start-object', metavar='<MIB::Object|OID>', type=_parse_mib_object,
        default=univ.ObjectIdentifier('1.3.6'),
        help='Drop all simulation data records prior to this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--stop-object', metavar='<MIB::Object|OID>',
        type=functools.partial(_parse_mib_object, last=True),
        help='Drop all simulation data records after this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--mib-source', dest='mib_sources', metavar='<URI|PATH>',
        action='append', type=str,
        default=['http://mibs.snmplabs.com/asn1/@mib@'],
        help='One or more URIs pointing to a collection of ASN.1 MIB files.'
             'Optional "@mib@" token gets replaced with desired MIB module '
             'name during MIB search.')

    parser.add_argument(
        '--destination-record-type', choices=RECORD_TYPES, default='snmprec',
        help='Produce simulation data with record of this type')

    parser.add_argument(
        '--output-file', metavar='<FILE>', type=str,
        help='SNMP simulation data file to write records to')

    variation_group = parser.add_argument_group(
        'Simulation data variation options')

    variation_group.add_argument(
        '--variation-modules-dir', action='append', type=str,
        help='Search variation module by this path')

    variation_group.add_argument(
        '--variation-module', type=str,
        help='Pass gathered simulation data through this variation module')

    variation_group.add_argument(
        '--variation-module-options', type=str, default='',
        help='Variation module options')

    parser.add_argument(
        '--output-dir', metavar='<FILE>', type=str, default='.',
        help='SNMP simulation data directory to place captured traffic in '
             'form of simulation records. File names reflect traffic sources '
             'on the network.')

    variation_group.add_argument(
        '--transport-id-offset', type=int, default=0,
        help='When arranging simulation data files, start enumerating '
             'receiving transport endpoints from this number.')

    traffic_group = parser.add_argument_group('Traffic capturing options')

    traffic_group.add_argument(
        '--packet-filter', type=str, default='udp and src port 161',
        help='Traffic filter (in tcpdump syntax) to use for picking SNMP '
             'packets out of the rest of the traffic.')

    variation_group.add_argument(
        '--listen-interface', type=str,
        help='Listen on this network interface.')

    parser.add_argument(
        '--promiscuous-mode', action='store_true',
        help='Attempt to switch NIC to promiscuous mode. Depending on the '
             'network, this may make traffic of surrounding machines visible. '
             'Might require superuser privileges.')

    parser.add_argument(
        '--capture-file', metavar='<FILE>', type=str,
        help='PCAP file with SNMP simulation data file to read from '
             'instead of listening on a NIC.')

    args = parser.parse_args()

    if not pcap:
        sys.stderr.write(
            'ERROR: pylibpcap package is missing!\r\nGet it by running '
            '`pip install '
            'https://downloads.sourceforge.net/project/pylibpcap/pylibpcap'
            '/0.6.4/pylibpcap-0.6.4.tar.gz`'
            '\r\n')
        parser.print_usage(sys.stderr)
        return 1

    try:
        log.setLogger(__name__, *args.logging_method, force=True)

        if args.log_level:
            log.setLevel(args.log_level)

    except error.SnmpsimError as exc:
        sys.stderr.write('%s\r\n%s\r\n' % exc)
        parser.print_usage(sys.stderr)
        sys.exit(1)

    if (isinstance(args.start_object, rfc1902.ObjectIdentity) or
            isinstance(args.stop_object, rfc1902.ObjectIdentity)):
        mibBuilder = builder.MibBuilder()

        mibViewController = view.MibViewController(mibBuilder)

        compiler.addMibCompiler(mibBuilder, sources=args.mib_sources)

        try:
            if isinstance(args.start_object, rfc1902.ObjectIdentity):
                args.start_object.resolveWithMib(mibViewController)

            if isinstance(args.stop_object, rfc1902.ObjectIdentity):
                args.stop_object.resolveWithMib(mibViewController)

        except PySnmpError as exc:
            sys.stderr.write('ERROR: %s\r\n' % exc)
            return 1

    # Load variation module

    if args.variation_module:

        for variation_modules_dir in (
                args.variation_modules_dir or confdir.variation):
            log.info('Scanning "%s" directory for variation '
                     'modules...' % variation_modules_dir)

            if not os.path.exists(variation_modules_dir):
                log.info('Directory "%s" does not exist' % variation_modules_dir)
                continue

            mod = os.path.join(variation_modules_dir, args.variation_module + '.py')
            if not os.path.exists(mod):
                log.info('Variation module "%s" not found' % mod)
                continue

            ctx = {'path': mod, 'moduleContext': {}}

            try:
                if sys.version_info[0] > 2:
                    exec(compile(open(mod).read(), mod, 'exec'), ctx)

                else:
                    execfile(mod, ctx)

            except Exception as exc:
                log.error('Variation module "%s" execution '
                          'failure: %s' % (mod, exc))
                return 1

            else:
                variation_module = ctx
                log.info('Variation module "%s" loaded' % args.variation_module)
                break

        else:
            log.error('variation module "%s" not found' % args.variation_module)
            return 1

    # Variation module initialization

    if variation_module:
        log.info('Initializing variation module...')

        for handler in ('init', 'record', 'shutdown'):
            if handler not in variation_module:
                log.error('missing "%s" handler at variation module '
                          '"%s"' % (handler, args.variation_module))
                return 1

        handler = variation_module['init']

        try:
            handler(options=args.variation_module_options, mode='recording',
                    startOID=args.start_object, stopOID=args.stop_object)

        except Exception as exc:
            log.error('Variation module "%s" initialization '
                      'FAILED: %s' % (args.variation_module, exc))

        else:
            log.info('Variation module "%s" '
                     'initialization OK' % args.variation_module)

    pcapObj = pcap.pcapObject()

    if args.listen_interface:
        if not args.quiet:
            log.info(
                'Listening on interface %s in %spromiscuous '
                'mode' % (args.listen_interface,
                          '' if args.promiscuous_mode else 'non-'))

        try:
            pcapObj.open_live(
                args.listen_interface, 65536, args.promiscuous_mode, 1000)

        except Exception as exc:
            log.error(
                'Error opening interface %s for snooping: '
                '%s' % (args.listen_interface, exc))
            return 1

    elif args.capture_file:
        if not args.quiet:
            log.info('Opening capture file %s' % args.capture_file)

        try:
            pcapObj.open_offline(args.capture_file)

        except Exception as exc:
            log.error('Error opening capture file %s for reading: '
                      '%s' % (args.capture_file, exc))
            return 1

    else:
        sys.stderr.write(
            'ERROR: no capture file or live interface specified\r\n')
        parser.print_usage(sys.stderr)
        return 1

    if args.packet_filter:
        if not args.quiet:
            log.info('Applying packet filter \"%s\"' % args.packet_filter)

        pcapObj.setfilter(args.packet_filter, 0, 0)

    if not args.quiet:
        log.info('Processing records from %still '
                 '%s' % ('the beginning ' if args.start_object
                                          else args.start_object,
                         args.stop_object if args.stop_object
                         else 'the end'))

    def parsePacket(raw):
        pkt = {}

        # http://www.tcpdump.org/linktypes.html
        llHeaders = {
            0: 4,
            1: 14,
            108: 4,
            228: 0
        }

        if pcapObj.datalink() in llHeaders:
            raw = raw[llHeaders[pcapObj.datalink()]:]

        else:
            stats['unknown L2 protocol'] += 1

        pkt['version'] = (ord(raw[0]) & 0xf0) >> 4
        pkt['header_len'] = ord(raw[0]) & 0x0f
        pkt['tos'] = ord(raw[1])
        pkt['total_len'] = socket.ntohs(
            struct.unpack('H', raw[2:4])[0])
        pkt['id'] = socket.ntohs(
            struct.unpack('H', raw[4:6])[0])
        pkt['flags'] = (ord(raw[6]) & 0xe0) >> 5
        pkt['fragment_offset'] = socket.ntohs(
            struct.unpack('H', raw[6:8])[0] & 0x1f)
        pkt['ttl'] = ord(raw[8])
        pkt['protocol'] = ord(raw[9])
        pkt['checksum'] = socket.ntohs(
            struct.unpack('H', raw[10:12])[0])
        pkt['source_address'] = pcap.ntoa(
            struct.unpack('i', raw[12:16])[0])
        pkt['destination_address'] = pcap.ntoa(
            struct.unpack('i', raw[16:20])[0])

        if pkt['header_len'] > 5:
            pkt['options'] = raw[20:4 * (pkt['header_len'] - 5)]

        else:
            pkt['options'] = None

        raw = raw[4 * pkt['header_len']:]

        if pkt['protocol'] == 17:
            pkt['source_port'] = socket.ntohs(
                struct.unpack('H', raw[0:2])[0])
            pkt['destination_port'] = socket.ntohs(
                struct.unpack('H', raw[2:4])[0])
            raw = raw[8:]
            stats['UDP packets'] += 1

        pkt['data'] = raw
        stats['IP packets'] += 1

        return pkt

    def handleSnmpMessage(d, t, private={}):
        msgVer = api.decodeMessageVersion(d['data'])

        if msgVer in api.protoModules:
            pMod = api.protoModules[msgVer]

        else:
            stats['bad packets'] += 1
            return

        try:
            rspMsg, wholeMsg = decoder.decode(
                d['data'], asn1Spec=pMod.Message())

        except PyAsn1Error:
            stats['bad packets'] += 1
            return

        if rspMsg['data'].getName() == 'response':
            rspPDU = pMod.apiMessage.getPDU(rspMsg)
            errorStatus = pMod.apiPDU.getErrorStatus(rspPDU)

            if errorStatus:
                stats['SNMP errors'] += 1

            else:
                endpoint = d['source_address'], d['source_port']

                if endpoint not in endpoints:
                    endpoints[endpoint] = udp.domainName + (
                        args.transport_id_offset + len(endpoints),)
                    stats['agents seen'] += 1

                context = '%s/%s' % (
                    pMod.ObjectIdentifier(endpoints[endpoint]),
                    pMod.apiMessage.getCommunity(rspMsg))

                if context not in contexts:
                    contexts[context] = {}
                    stats['contexts seen'] += 1

                context = '%s/%s' % (
                    pMod.ObjectIdentifier(endpoints[endpoint]),
                    pMod.apiMessage.getCommunity(rspMsg))

                stats['Response PDUs seen'] += 1

                if 'basetime' not in private:
                    private['basetime'] = t

                for oid, value in pMod.apiPDU.getVarBinds(rspPDU):
                    if oid < args.start_object:
                        continue

                    if args.stop_object and oid >= args.stop_object:
                        continue

                    if oid in contexts[context]:
                        if value != contexts[context][oid]:
                            stats['snapshots taken'] += 1

                    else:
                        contexts[context][oid] = [], []

                    contexts[context][oid][0].append(t - private['basetime'])
                    contexts[context][oid][1].append(value)

                    stats['OIDs seen'] += 1

    def handlePacket(pktlen, data, timestamp):
        if not data:
            stats['empty packets'] += 1
            return

        handleSnmpMessage(parsePacket(data), timestamp)

    try:
        if args.listen_interface:
            log.info(
                'Listening on interface "%s", kill me when you '
                'are done.' % args.listen_interface)

            while True:
                pcapObj.dispatch(1, handlePacket)

        elif args.capture_file:
            log.info('Processing capture file "%s"....' % args.capture_file)

            args = pcapObj.next()

            while args:
                handlePacket(*args)
                args = pcapObj.next()

    except (TypeError, KeyboardInterrupt):
        log.info('Shutting down process...')

    finally:
        dataFileHandler = SnmprecRecord()

        for context in contexts:
            ext = os.path.extsep + RECORD_TYPES[args.destination_record_type].ext

            filename = os.path.join(args.output_dir, context + ext)

            if not args.quiet:
                log.info(
                    'Creating simulation context %s at '
                    '%s' % (context, filename))

            try:
                os.mkdir(os.path.dirname(filename))

            except OSError:
                pass

            try:
                outputFile = RECORD_TYPES[args.destination_record_type].open(filename, 'wb')

            except IOError as exc:
                log.error('writing %s: %s' % (filename, exc))
                return 1

            count = total = iteration = 0
            timeOffset = 0
            reqTime = time.time()

            oids = sorted(contexts[context])
            oids.append(oids[-1])  # duplicate last OID to trigger stopFlag

            while True:
                for oid in oids:

                    timeline, values = contexts[context][oid]

                    value = values[
                        min(len(values) - 1,
                            bisect.bisect_left(timeline, timeOffset))
                    ]

                    if value.tagSet in (rfc1905.NoSuchObject.tagSet,
                                        rfc1905.NoSuchInstance.tagSet,
                                        rfc1905.EndOfMibView.tagSet):
                        stats['SNMP exceptions'] += 1
                        continue

                    # remove value enumeration

                    if value.tagSet == Integer32.tagSet:
                        value = Integer32(value)

                    if value.tagSet == Unsigned32.tagSet:
                        value = Unsigned32(value)

                    if value.tagSet == Bits.tagSet:
                        value = OctetString(value)

                    # Build .snmprec record

                    ctx = {
                        'origOid': oid,
                        'origValue': value,
                        'count': count,
                        'total': total,
                        'iteration': iteration,
                        'reqTime': reqTime,
                        'startOID': args.start_object,
                        'stopOID': args.stop_object,
                        'stopFlag': oids.index(oid) == len(oids) - 1,
                        'variationModule': variation_module
                    }

                    try:
                        line = dataFileHandler.format(oid, value, **ctx)

                    except error.MoreDataNotification as exc:
                        count = 0
                        iteration += 1

                        moreDataNotification = exc
                        if 'period' in moreDataNotification:
                            timeOffset += moreDataNotification['period']
                            log.info(
                                '%s OIDs dumped, advancing time window to '
                                '%.2f sec(s)...' % (total, timeOffset))
                        break

                    except error.NoDataNotification:
                        pass

                    except error.SnmpsimError as exc:
                        log.error(exc)
                        continue

                    else:
                        outputFile.write(line)

                        count += 1
                        total += 1

                else:
                    break

            outputFile.flush()
            outputFile.close()

        if variation_module:
            log.info('Shutting down variation module '
                     '"%s"...' % args.variation_module)

            handler = variation_module['shutdown']

            try:
                handler(options=args.variation_module_options, mode='recording')

            except Exception as exc:
                log.error('Variation module "%s" shutdown FAILED: '
                          '%s' % (args.variation_module, exc))

            else:
                log.info('Variation module "%s" shutdown OK' % args.variation_module)

        log.info("""\
PCap statistics:
    packets snooped: %s
    packets dropped: %s
    packets dropped: by interface %s\
    """ % pcapObj.stats())

        log.info("""\
SNMP statistics:
    %s\
    """ % '    '.join(['%s: %s\r\n' % kv for kv in stats.items()]))

    return 0


if __name__ == '__main__':
    try:
        rc = main()

    except KeyboardInterrupt:
        sys.stderr.write('shutting down process...')
        rc = 0

    except Exception as exc:
        sys.stderr.write('process terminated: %s' % exc)

        for line in traceback.format_exception(*sys.exc_info()):
            sys.stderr.write(line.replace('\n', ';'))
        rc = 1

    sys.exit(rc)
