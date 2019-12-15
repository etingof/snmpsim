#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Simulator MIB to data file converter
#
import argparse
import functools
import os
import random
import sys
import traceback

from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pysnmp import debug
from pysnmp.proto import rfc1902
from pysnmp.smi import builder
from pysnmp.smi import compiler
from pysnmp.smi import error
from pysnmp.smi import view
from pysnmp.smi.rfc1902 import ObjectIdentity

from snmpsim import utils
from snmpsim.error import SnmpsimError
from snmpsim.record import dump
from snmpsim.record import mvc
from snmpsim.record import sap
from snmpsim.record import snmprec
from snmpsim.record import walk

RECORD_TYPES = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
    snmprec.SnmprecRecord.ext: snmprec.SnmprecRecord(),
    snmprec.CompressedSnmprecRecord.ext: snmprec.CompressedSnmprecRecord()
}

DESCRIPTION = (
    'Converts MIB modules into SNMP simulation data files. '
    'Chooses random values or asks interactively. '
    'Fills SNMP conceptual tables with consistent indices.')


def _parse_mib_object(arg, last=False):
    if '::' in arg:
        return ObjectIdentity(*arg.split('::', 1), last=last)

    else:
        return univ.ObjectIdentifier(arg)


def _parse_range(arg):
    try:
        minimum, maximum = [int(x) for x in arg.split(',')]

    except Exception as exc:
        raise SnmpsimError('Malformed integer range %s: %s' % (arg, exc))

    return minimum, maximum


def main():

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument(
        '-v', '--version', action='version',
        version=utils.TITLE)

    parser.add_argument(
        '--quiet', action='store_true',
        help='Do not print out informational messages')

    parser.add_argument(
        '--debug', choices=debug.flagMap,
        action='append', type=str, default=[],
        help='Enable one or more categories of SNMP debugging.')

    parser.add_argument(
        '--mib-source', dest='mib_sources', metavar='<URI|PATH>',
        action='append', type=str,
        default=['http://mibs.snmplabs.com/asn1/@mib@'],
        help='One or more URIs pointing to a collection of ASN.1 MIB files.'
             'Optional "@mib@" token gets replaced with desired MIB module '
             'name during MIB search.')

    parser.add_argument(
        '--mib-module', dest='mib_modules', action='append',
        type=str, required=True,
        help='MIB module to generate simulation data from')

    parser.add_argument(
        '--start-object', metavar='<MIB::Object|OID>', type=_parse_mib_object,
        help='Drop all simulation data records prior to this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--stop-object', metavar='<MIB::Object|OID>',
        type=functools.partial(_parse_mib_object, last=True),
        help='Drop all simulation data records after this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--manual-values', action='store_true',
        help='Fill all managed objects values interactively')

    parser.add_argument(
        '--automatic-values', type=int, default=5000,
        help='Probe for suitable managed object value this many times '
             'prior to failing over to manual value specification')

    parser.add_argument(
        '--table-size', type=int, default=10,
        help='Generate SNMP conceptual tables with this many rows')

    parser.add_argument(
        '--destination-record-type', choices=RECORD_TYPES, default='snmprec',
        help='Produce simulation data with record of this type')

    parser.add_argument(
        '--output-file', metavar='<FILE>', type=str,
        help='SNMP simulation data file to write records to')

    parser.add_argument(
        '--string-pool', metavar='<words>', action='append',
        help='Words to use for simulated string values')

    parser.add_argument(
        '--string-pool-file', metavar='<FILE>', type=str,
        help='File containing the words for simulating SNMP string values')

    parser.add_argument(
        '--integer32-range', metavar='<min,max>',
        type=_parse_range, default=(0, 32),
        help='Range of values used to populate simulated Integer32 values')

    parser.add_argument(
        '--unsigned-range', metavar='<min,max>',
        type=_parse_range, default=(0, 65535),
        help='Range of values used to populate simulated Unsigned values')

    parser.add_argument(
        '--counter-range', metavar='<min,max>',
        type=_parse_range, default=(0, 0xffffffff),
        help='Range of values used to populate simulated Counter values')

    parser.add_argument(
        '--counter64-range', metavar='<min,max>',
        type=_parse_range, default=(0, 0xffffffffffffffff),
        help='Range of values used to populate simulated Counter64 values')

    parser.add_argument(
        '--gauge-range', metavar='<min,max>',
        type=_parse_range, default=(0, 0xffffffff),
        help='Range of values used to populate simulated Gauge values')

    parser.add_argument(
        '--timeticks-range', metavar='<min,max>',
        type=_parse_range, default=(0, 0xffffffff),
        help='Range of values used to populate simulated Timeticks values')

    args = parser.parse_args()

    if args.debug:
        debug.setLogger(debug.Debug(*args.debug))

    if args.manual_values:
        args.automatic_values = 0

    if args.string_pool_file:
        with open(args.string_pool_file) as fl:
            args.string_pool = fl.read().split()

    elif args.string_pool:
        args.string_pool = ['Jaded', 'zombies', 'acted', 'quaintly', 'but',
                            'kept', 'driving', 'their', 'oxen', 'forward']

    if args.output_file:
        ext = os.path.extsep + RECORD_TYPES[args.destination_record_type].ext

        if not args.output_file.endswith(ext):
            args.output_file += ext

        args.output_file = RECORD_TYPES[args.destination_record_type].open(
            args.output_file, 'wb')

    else:
        args.output_file = sys.stdout

        if sys.version_info >= (3, 0, 0):
            # binary mode write
            args.output_file = sys.stdout.buffer

        elif sys.platform == "win32":
            import msvcrt

            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    def getValue(syntax, hint='', automatic_values=args.automatic_values):

        makeGuess = args.automatic_values

        val = None

        while True:
            if makeGuess:
                if isinstance(syntax, rfc1902.IpAddress):
                    val = '.'.join([str(random.randrange(1, 256)) for x in range(4)])

                elif isinstance(syntax, rfc1902.TimeTicks):
                    val = random.randrange(args.timeticks_range[0], args.timeticks_range[1])

                elif isinstance(syntax, rfc1902.Gauge32):
                    val = random.randrange(args.gauge_range[0], args.gauge_range[1])

                elif isinstance(syntax, rfc1902.Counter32):
                    val = random.randrange(args.counter_range[0], args.counter_range[1])

                elif isinstance(syntax, rfc1902.Integer32):
                    val = random.randrange(args.integer32_range[0], args.integer32_range[1])

                elif isinstance(syntax, rfc1902.Unsigned32):
                    val = random.randrange(args.unsigned_range[0], args.unsigned_range[1])

                elif isinstance(syntax, rfc1902.Counter64):
                    val = random.randrange(args.counter64_range[0], args.counter64_range[1])

                elif isinstance(syntax, univ.OctetString):
                    maxWords = 10
                    val = ' '.join([args.string_pool[random.randrange(0, len(args.string_pool))]
                                    for i in range(random.randrange(1, maxWords))])

                elif isinstance(syntax, univ.ObjectIdentifier):
                    val = '.'.join(['1', '3', '6', '1', '3'] + [
                        '%d' % random.randrange(0, 255)
                        for x in range(random.randrange(0, 10))])

                elif isinstance(syntax, rfc1902.Bits):
                    val = [random.randrange(0, 256)
                           for x in range(random.randrange(0, 9))]

                else:
                    val = '?'

            # remove value enumeration

            try:
                if syntax.tagSet == rfc1902.Integer32.tagSet:
                    return rfc1902.Integer32(syntax.clone(val))

                if syntax.tagSet == rfc1902.Unsigned32.tagSet:
                    return rfc1902.Unsigned32(syntax.clone(val))

                if syntax.tagSet == rfc1902.Bits.tagSet:
                    return rfc1902.OctetString(syntax.clone(val))

                return syntax.clone(val)

            except PyAsn1Error as exc:
                if makeGuess == 1:
                    sys.stderr.write(
                        '*** Inconsistent value: %s\r\n*** See constraints and '
                        'suggest a better one for:\r\n' % exc)

                if makeGuess:
                    makeGuess -= 1
                    continue

            sys.stderr.write('%s# Value [\'%s\'] ? ' % (
                hint, (val is None and '<none>' or val),))
            sys.stderr.flush()

            line = sys.stdin.readline().strip()

            if line:
                if line[:2] == '0x':
                    if line[:4] == '0x0x':
                        line = line[2:]

                    elif isinstance(syntax, univ.OctetString):
                        val = syntax.clone(hexValue=line[2:])

                    else:
                        val = int(line[2:], 16)

                else:
                    val = line

    dataFileHandler = snmprec.SnmprecRecord()

    mibBuilder = builder.MibBuilder()

    # Load MIB tree foundation classes
    (MibScalar,
     MibTable,
     MibTableRow,
     MibTableColumn) = mibBuilder.importSymbols(
        'SNMPv2-SMI',
        'MibScalar',
        'MibTable',
        'MibTableRow',
        'MibTableColumn'
    )

    mibViewController = view.MibViewController(mibBuilder)

    compiler.addMibCompiler(mibBuilder, sources=args.mib_sources)

    try:
        if isinstance(args.start_object, ObjectIdentity):
            args.start_object.resolveWithMib(mibViewController)

        if isinstance(args.stop_object, ObjectIdentity):
            args.stop_object.resolveWithMib(mibViewController)

    except error.PySnmpError as exc:
        sys.stderr.write('ERROR: %s\r\n' % exc)
        return 1

    output = []

    # MIBs walk
    for modName in args.mib_modules:
        if not args.quiet:
            sys.stderr.write(
                '# MIB module: %s, from %s till '
                '%s\r\n' % (modName, args.start_object or 'the beginning',
                            args.stop_object or 'the end'))

        try:
            oid = ObjectIdentity(modName).resolveWithMib(mibViewController)

        except error.PySnmpError as exc:
            sys.stderr.write('ERROR: failed on MIB %s: '
                             '%s\r\n' % (modName, exc))
            return 1

        hint = rowHint = ''
        rowOID = None
        suffix = ()
        thisTableSize = 0

        while True:
            try:
                oid, label, _ = mibViewController.getNextNodeName(oid)

            except error.NoSuchObjectError:
                break

            if rowOID and not rowOID.isPrefixOf(oid):
                thisTableSize += 1

                if args.automatic_values:
                    if thisTableSize < args.table_size:
                        oid = tuple(rowOID)
                        if not args.quiet:
                            sys.stderr.write(
                                '# Synthesizing row #%d of table %s\r\n' % (
                                    thisTableSize, rowOID))

                    else:
                        if not args.quiet:
                            sys.stderr.write(
                                '# Finished table %s (%d rows)\r\n' % (
                                    rowOID, thisTableSize))

                        rowOID = None

                else:
                    while True:
                        sys.stderr.write(
                            '# Synthesize row #%d for table %s (y/n)? ' % (
                                thisTableSize, rowOID))
                        sys.stderr.flush()

                        line = sys.stdin.readline().strip()
                        if line:
                            if line[0] in ('y', 'Y'):
                                oid = tuple(rowOID)
                                break

                            elif line[0] in ('n', 'N'):
                                if not args.quiet:
                                    sys.stderr.write(
                                        '# Finished table %s (%d rows)\r\n' % (
                                            rowOID, thisTableSize))
                                rowOID = None
                                break

            if args.start_object and oid < args.start_object:
                continue  # skip on premature OID

            if args.stop_object and oid > args.stop_object:
                break  # stop on out of range condition

            mibName, symName, _ = mibViewController.getNodeLocation(oid)
            node, = mibBuilder.importSymbols(mibName, symName)

            if isinstance(node, MibTable):
                hint = '# Table %s::%s\r\n' % (mibName, symName)
                if not args.quiet:
                    sys.stderr.write(
                        '# Starting table %s::%s (%s)\r\n' % (
                            mibName, symName, univ.ObjectIdentifier(oid)))
                continue

            elif isinstance(node, MibTableRow):
                rowIndices = {}
                suffix = ()
                rowHint = hint + '# Row %s::%s\r\n' % (mibName, symName)

                for impliedFlag, idxModName, idxSymName in node.getIndexNames():
                    idxNode, = mibBuilder.importSymbols(idxModName, idxSymName)

                    rowHint += '# Index %s::%s (type %s)\r\n' % (
                        idxModName, idxSymName, idxNode.syntax.__class__.__name__)

                    rowIndices[idxNode.name] = getValue(
                        idxNode.syntax, not args.quiet and rowHint or '')

                    suffix = suffix + node.getAsName(
                        rowIndices[idxNode.name], impliedFlag)

                if not rowIndices:
                    if not args.quiet:
                        sys.stderr.write(
                            '# WARNING: %s::%s table has no index!\r\n' % (
                                mibName, symName))

                if rowOID is None:
                    thisTableSize = 0

                rowOID = univ.ObjectIdentifier(oid)
                continue

            elif isinstance(node, MibTableColumn):
                oid = node.name
                if oid in rowIndices:
                    val = rowIndices[oid]

                else:
                    val = getValue(
                        node.syntax, not args.quiet and (
                                rowHint + '# Column %s::%s (type'
                                          ' %s)\r\n' % (mibName, symName,
                                                        node.syntax.__class__.__name__) or ''))

            elif isinstance(node, MibScalar):
                hint = ''
                oid = node.name
                suffix = (0,)
                val = getValue(
                    node.syntax, not args.quiet and '# Scalar %s::%s (type %s)\r\n' % (
                        mibName, symName, node.syntax.__class__.__name__) or '')

            else:
                hint = ''
                continue

            output.append((oid + suffix, val))

        output.sort(key=lambda x: univ.ObjectIdentifier(x[0]))

        unique = set()

        for oid, val in output:
            if oid in unique:
                if not args.quiet:
                    sys.stderr.write(
                        '# Dropping duplicate OID %s\r\n' % (
                            univ.ObjectIdentifier(oid),))
            else:
                try:
                    args.output_file.write(dataFileHandler.format(oid, val))

                except SnmpsimError as exc:
                    sys.stderr.write('ERROR: %s\r\n' % (exc,))

                else:
                    unique.add(oid)

        if not args.quiet:
            sys.stderr.write(
                '# End of %s, %s OID(s) dumped\r\n' % (modName, len(unique)))

    args.output_file.flush()
    args.output_file.close()

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
