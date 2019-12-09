#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Simulator MIB to data file converter
#
import getopt
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

HELP_MESSAGE = """\
Usage: %s [--help]
    [--version]
    [--debug=<%s>]
    [--quiet]
    [--mib-source=<url>]
    [--pysnmp-mib-dir=</path/to/pysnmp/mibs]
    [--mib-module=<MIB-NAME>]
    [--start-object=<MIB-NAME::[symbol-name]|OID>]
    [--stop-object=<MIB-NAME::[symbol-name]|OID>]
    [--manual-values]
    [--automatic-values=<max-probes>]
    [--table-size=<number>]
    [--destination-record-type=<%s>]
    [--output-file=<filename>]
    [--string-pool=<words>]
    [--string-pool-file=</path/to/text/file>]
    [--counter-range=<min,max>]
    [--counter64-range=<min,max>]
    [--gauge-range=<min,max>]
    [--timeticks-range=<min,max>]
    [--unsigned-range=<min,max>]
    [--integer32-range=<min,max>]\
""" % (sys.argv[0],
       '|'.join([x for x in getattr(debug, 'FLAG_MAP', getattr(debug, 'flagMap', ()))
                 if x not in ('app', 'msgproc', 'proxy', 'io', 'secmod',
                              'dsp', 'acl')]),
       '|'.join(RECORD_TYPES))

PROGRAM_NAME = os.path.basename(sys.argv[0])


def main():
    # Defaults
    verboseFlag = True
    startOID = stopOID = None
    mibSources = []
    defaultMibSources = ['http://mibs.snmplabs.com/asn1/@mib@']
    dstRecordType = 'snmprec'
    outputFile = None
    stringPool = 'Jaded zombies acted quaintly but kept driving their oxen forward'.split()
    counterRange = 0, 0xffffffff
    counter64Range = 0, 0xffffffffffffffff
    gaugeRange = 0, 0xffffffff
    timeticksRange = 0, 0xffffffff
    unsignedRange = 0, 65535
    int32Range = 0, 32  # these values are more likely to fit constraints
    automaticValues = 5000
    tableSize = 10
    modNames = []
    mibDirs = []

    try:
        opts, params = getopt.getopt(
            sys.argv[1:], 'hv',
            ['help', 'version', 'debug=', 'quiet',
             'pysnmp-mib-dir=', 'mib-module=', 'start-oid=', 'stop-oid=',
             'mib-source=', 'start-object=', 'stop-object=',
             'manual-values', 'automatic-values=', 'table-size=',
             'destination-record-type=',
             'output-file=', 'string-pool=', 'string-pool-file=',
             'integer32-range=', 'counter-range=', 'counter64-range=',
             'gauge-range=', 'unsigned-range=', 'timeticks-range='])

    except Exception as exc:
        sys.stderr.write('ERROR: %s\r\n%s\r\n' % (exc, HELP_MESSAGE))
        return 1

    if params:
        sys.stderr.write('ERROR: extra arguments supplied %s\r\n'
                         '%s\r\n' % (params, HELP_MESSAGE))
        return 1

    for opt in opts:

        if opt[0] == '-h' or opt[0] == '--help':
            sys.stderr.write("""\
Synopsis:
  Converts MIB modules into SNMP Simulator data files.
  Chooses random values or can ask for them interactively.
  Able to fill SNMP conceptual tables with consistent indices.

Documentation:
  http://snmplabs.com/snmpsim/simulation-based-on-mibs.html
%s
""" % HELP_MESSAGE)
            return 1

        if opt[0] == '-v' or opt[0] == '--version':
            import snmpsim
            import pysmi
            import pysnmp
            import pyasn1

            sys.stderr.write("""\
SNMP Simulator version %s, written by Ilya Etingof <etingof@gmail.com>
Using foundation libraries: pysmi %s, pysnmp %s, pyasn1 %s.
Python interpreter: %s
Software documentation and support at http://snmplabs.com/snmpsim
%s
""" % (snmpsim.__version__,
           getattr(pysmi, '__version__', 'unknown'),
           getattr(pysnmp, '__version__', 'unknown'),
           getattr(pyasn1, '__version__', 'unknown'),
           sys.version, HELP_MESSAGE))
            return 1

        if opt[0] == '--debug':
            debug.setLogger(debug.Debug(*opt[1].split(',')))

        if opt[0] == '--quiet':
            verboseFlag = False

        if opt[0] == '--pysnmp-mib-dir':
            mibDirs.append(opt[1])

        if opt[0] == '--mib-module':
            modNames.append(opt[1])

        # obsolete begin
        if opt[0] == '--start-oid':
            startOID = univ.ObjectIdentifier(opt[1])

        if opt[0] == '--stop-oid':
            stopOID = univ.ObjectIdentifier(opt[1])
        # obsolete end

        if opt[0] == '--mib-source':
            mibSources.append(opt[1])

        if opt[0] == '--start-object':
            startOID = ObjectIdentity(
                *opt[1].split('::', 1))

        if opt[0] == '--stop-object':
            stopOID = ObjectIdentity(
                *opt[1].split('::', 1), **dict(last=True))

        if opt[0] == '--manual-values':
            automaticValues = 0

        if opt[0] == '--automatic-values':
            try:
                automaticValues = int(opt[1])

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--table-size':
            try:
                tableSize = int(opt[1])

            except ValueError as exc:
                sys.stderr.write('ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--destination-record-type':
            if opt[1] not in RECORD_TYPES:
                sys.stderr.write(
                    'ERROR: unknown record type <%s> (known types are %s)\r\n%s'
                    '\r\n' % (opt[1], ', '.join(RECORD_TYPES),
                              HELP_MESSAGE))
                return 1

            dstRecordType = opt[1]

        if opt[0] == '--output-file':
            outputFile = open(opt[1], 'wb')

        if opt[0] == '--string-pool':
            stringPool = opt[1].split()

        if opt[0] == '--string-pool-file':
            try:
                f = open(opt[1])
                stringPool = f.read().split()
                f.close()

            except Exception as exc:
                sys.stderr.write(
                    'ERROR: text file "%s" open failure '
                    '%s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--counter-range':
            try:
                counterRange = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--counter64-range':
            try:
                counter64Range = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--gauge-range':
            try:
                gaugeRange = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--timeticks-range':
            try:
                timeticksRange = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--integer32-range':
            try:
                int32Range = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write(
                    'ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

        if opt[0] == '--unsigned-range':
            try:
                unsignedRange = [int(x) for x in opt[1].split(',')]

            except ValueError as exc:
                sys.stderr.write('ERROR: bad value %s: %s\r\n' % (opt[1], exc))
                return 1

    if outputFile:
        ext = os.path.extsep + RECORD_TYPES[dstRecordType].ext

        if not outputFile.endswith(ext):
            outputFile += ext

        outputFile = RECORD_TYPES[dstRecordType].open(outputFile, 'wb')

    else:
        outputFile = sys.stdout

        if sys.version_info >= (3, 0, 0):
            # binary mode write
            outputFile = sys.stdout.buffer

        elif sys.platform == "win32":
            import msvcrt

            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    # Catch missing params
    if not modNames:
        sys.stderr.write(
            'ERROR: MIB modules not specified\r\n%s\r\n' % HELP_MESSAGE)
        return 1

    def getValue(syntax, hint='', automaticValues=automaticValues):

        makeGuess = automaticValues

        val = None

        while True:
            if makeGuess:
                if isinstance(syntax, rfc1902.IpAddress):
                    val = '.'.join([str(random.randrange(1, 256)) for x in range(4)])

                elif isinstance(syntax, rfc1902.TimeTicks):
                    val = random.randrange(timeticksRange[0], timeticksRange[1])

                elif isinstance(syntax, rfc1902.Gauge32):
                    val = random.randrange(gaugeRange[0], gaugeRange[1])

                elif isinstance(syntax, rfc1902.Counter32):
                    val = random.randrange(counterRange[0], counterRange[1])

                elif isinstance(syntax, rfc1902.Integer32):
                    val = random.randrange(int32Range[0], int32Range[1])

                elif isinstance(syntax, rfc1902.Unsigned32):
                    val = random.randrange(unsignedRange[0], unsignedRange[1])

                elif isinstance(syntax, rfc1902.Counter64):
                    val = random.randrange(counter64Range[0], counter64Range[1])

                elif isinstance(syntax, univ.OctetString):
                    maxWords = 10
                    val = ' '.join([stringPool[random.randrange(0, len(stringPool))]
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

    mibBuilder.setMibSources(
        *mibBuilder.getMibSources() + tuple(
            [builder.ZipMibSource(m).init() for m in mibDirs]
        )
    )

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

    compiler.addMibCompiler(
        mibBuilder, sources=mibSources or defaultMibSources
    )

    try:
        if isinstance(startOID, ObjectIdentity):
            startOID.resolveWithMib(mibViewController)

        if isinstance(stopOID, ObjectIdentity):
            stopOID.resolveWithMib(mibViewController)

    except error.PySnmpError as exc:
        sys.stderr.write('ERROR: %s\r\n' % exc)
        return 1

    output = []

    # MIBs walk
    for modName in modNames:
        if verboseFlag:
            sys.stderr.write(
                '# MIB module: %s, from %s till '
                '%s\r\n' % (modName, startOID or 'the beginning',
                            stopOID or 'the end'))

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

                if automaticValues:
                    if thisTableSize < tableSize:
                        oid = tuple(rowOID)
                        if verboseFlag:
                            sys.stderr.write(
                                '# Synthesizing row #%d of table %s\r\n' % (
                                    thisTableSize, rowOID))

                    else:
                        if verboseFlag:
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
                                if verboseFlag:
                                    sys.stderr.write(
                                        '# Finished table %s (%d rows)\r\n' % (
                                            rowOID, thisTableSize))
                                rowOID = None
                                break

            if startOID and oid < startOID:
                continue  # skip on premature OID

            if stopOID and oid > stopOID:
                break  # stop on out of range condition

            mibName, symName, _ = mibViewController.getNodeLocation(oid)
            node, = mibBuilder.importSymbols(mibName, symName)

            if isinstance(node, MibTable):
                hint = '# Table %s::%s\r\n' % (mibName, symName)
                if verboseFlag:
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
                        idxNode.syntax, verboseFlag and rowHint or '')

                    suffix = suffix + node.getAsName(
                        rowIndices[idxNode.name], impliedFlag)

                if not rowIndices:
                    if verboseFlag:
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
                        node.syntax, verboseFlag and (
                                rowHint + '# Column %s::%s (type'
                                          ' %s)\r\n' % (mibName, symName,
                                                        node.syntax.__class__.__name__) or ''))

            elif isinstance(node, MibScalar):
                hint = ''
                oid = node.name
                suffix = (0,)
                val = getValue(
                    node.syntax, verboseFlag and '# Scalar %s::%s (type %s)\r\n' % (
                        mibName, symName, node.syntax.__class__.__name__) or '')

            else:
                hint = ''
                continue

            output.append((oid + suffix, val))

        output.sort(key=lambda x: univ.ObjectIdentifier(x[0]))

        unique = set()

        for oid, val in output:
            if oid in unique:
                if verboseFlag:
                    sys.stderr.write(
                        '# Dropping duplicate OID %s\r\n' % (
                            univ.ObjectIdentifier(oid),))
            else:
                try:
                    outputFile.write(dataFileHandler.format(oid, val))

                except SnmpsimError as exc:
                    sys.stderr.write('ERROR: %s\r\n' % (exc,))

                else:
                    unique.add(oid)

        if verboseFlag:
            sys.stderr.write(
                '# End of %s, %s OID(s) dumped\r\n' % (modName, len(unique)))

    outputFile.flush()
    outputFile.close()

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
