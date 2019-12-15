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

    def get_value(syntax, hint='', automatic_values=args.automatic_values):

        make_guess = args.automatic_values

        val = None

        while True:
            if make_guess:
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
                if make_guess == 1:
                    sys.stderr.write(
                        '*** Inconsistent value: %s\r\n*** See constraints and '
                        'suggest a better one for:\r\n' % exc)

                if make_guess:
                    make_guess -= 1
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

    data_file_handler = snmprec.SnmprecRecord()

    mib_builder = builder.MibBuilder()

    # Load MIB tree foundation classes
    (MibScalar,
     MibTable,
     MibTableRow,
     MibTableColumn) = mib_builder.importSymbols(
        'SNMPv2-SMI',
        'MibScalar',
        'MibTable',
        'MibTableRow',
        'MibTableColumn'
    )

    mib_view_controller = view.MibViewController(mib_builder)

    compiler.addMibCompiler(mib_builder, sources=args.mib_sources)

    try:
        if isinstance(args.start_object, ObjectIdentity):
            args.start_object.resolveWithMib(mib_view_controller)

        if isinstance(args.stop_object, ObjectIdentity):
            args.stop_object.resolveWithMib(mib_view_controller)

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
            oid = ObjectIdentity(modName).resolveWithMib(mib_view_controller)

        except error.PySnmpError as exc:
            sys.stderr.write('ERROR: failed on MIB %s: '
                             '%s\r\n' % (modName, exc))
            return 1

        hint = row_hint = ''
        row_oid = None
        suffix = ()
        this_table_size = 0

        while True:
            try:
                oid, label, _ = mib_view_controller.getNextNodeName(oid)

            except error.NoSuchObjectError:
                break

            if row_oid and not row_oid.isPrefixOf(oid):
                this_table_size += 1

                if args.automatic_values:
                    if this_table_size < args.table_size:
                        oid = tuple(row_oid)
                        if not args.quiet:
                            sys.stderr.write(
                                '# Synthesizing row #%d of table %s\r\n' % (
                                    this_table_size, row_oid))

                    else:
                        if not args.quiet:
                            sys.stderr.write(
                                '# Finished table %s (%d rows)\r\n' % (
                                    row_oid, this_table_size))

                        row_oid = None

                else:
                    while True:
                        sys.stderr.write(
                            '# Synthesize row #%d for table %s (y/n)? ' % (
                                this_table_size, row_oid))
                        sys.stderr.flush()

                        line = sys.stdin.readline().strip()
                        if line:
                            if line[0] in ('y', 'Y'):
                                oid = tuple(row_oid)
                                break

                            elif line[0] in ('n', 'N'):
                                if not args.quiet:
                                    sys.stderr.write(
                                        '# Finished table %s (%d rows)\r\n' % (
                                            row_oid, this_table_size))
                                row_oid = None
                                break

            if args.start_object and oid < args.start_object:
                continue  # skip on premature OID

            if args.stop_object and oid > args.stop_object:
                break  # stop on out of range condition

            mib_name, sym_name, _ = mib_view_controller.getNodeLocation(oid)
            node, = mib_builder.importSymbols(mib_name, sym_name)

            if isinstance(node, MibTable):
                hint = '# Table %s::%s\r\n' % (mib_name, sym_name)
                if not args.quiet:
                    sys.stderr.write(
                        '# Starting table %s::%s (%s)\r\n' % (
                            mib_name, sym_name, univ.ObjectIdentifier(oid)))
                continue

            elif isinstance(node, MibTableRow):
                row_indices = {}
                suffix = ()
                row_hint = hint + '# Row %s::%s\r\n' % (mib_name, sym_name)

                for (implied_flag,
                     idx_mod_name, idx_sym_name) in node.getIndexNames():
                    idxNode, = mib_builder.importSymbols(
                        idx_mod_name, idx_sym_name)

                    row_hint += '# Index %s::%s (type %s)\r\n' % (
                        idx_mod_name, idx_sym_name,
                        idxNode.syntax.__class__.__name__)

                    row_indices[idxNode.name] = get_value(
                        idxNode.syntax, not args.quiet and row_hint or '')

                    suffix = suffix + node.getAsName(
                        row_indices[idxNode.name], implied_flag)

                if not row_indices:
                    if not args.quiet:
                        sys.stderr.write(
                            '# WARNING: %s::%s table has no index!\r\n' % (
                                mib_name, sym_name))

                if row_oid is None:
                    this_table_size = 0

                row_oid = univ.ObjectIdentifier(oid)
                continue

            elif isinstance(node, MibTableColumn):
                oid = node.name
                if oid in row_indices:
                    val = row_indices[oid]

                else:
                    hint = ''
                    if not args.quiet:
                        hint += row_hint
                        hint += ('# Column %s::%s (type'
                                 ' %s)\r\n' % (mib_name, sym_name,
                                               node.syntax.__class__.__name__))

                    val = get_value(node.syntax, hint)

            elif isinstance(node, MibScalar):
                hint = ''
                if not args.row_hint:
                    hint += ('# Scalar %s::%s (type %s)'
                             '\r\n' % (mib_name, sym_name,
                                       node.syntax.__class__.__name__))
                oid = node.name
                suffix = (0,)
                val = get_value(node.syntax, hint)

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
                    args.output_file.write(data_file_handler.format(oid, val))

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
