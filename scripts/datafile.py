#!/usr/bin/env python
#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Simulator data file management tool
#
import getopt
import sys
import os

from pyasn1.type import univ
from pysnmp.error import PySnmpError
from pysnmp.smi import builder
from pysnmp.smi import compiler
from pysnmp.smi import rfc1902
from pysnmp.smi import view

from snmpsim import error
from snmpsim.record import dump
from snmpsim.record import mvc
from snmpsim.record import sap
from snmpsim.record import snmprec
from snmpsim.record import walk
from snmpsim.record.search.file import getRecord

# Defaults
verboseFlag = True
mibSources = []
defaultMibSources = ['http://mibs.snmplabs.com/asn1/@mib@']
sortRecords = ignoreBrokenRecords = deduplicateRecords = lostComments = False
startOID = stopOID = None
srcRecordType = dstRecordType = 'snmprec'
inputFiles = []
outputFile = None
escapedStrings = False

writtenCount = skippedCount = duplicateCount = brokenCount = variationCount = 0


class SnmprecRecordMixIn(object):

    def evaluateValue(self, oid, tag, value, **context):
        # Variation module reference
        if ':' in tag:
            context['backdoor']['textTag'] = tag
            return oid, '', value

        else:
            return snmprec.SnmprecRecord.evaluateValue(self, oid, tag, value)

    def formatValue(self, oid, value, **context):
        if 'textTag' in context['backdoor']:
            return self.formatOid(oid), context['backdoor']['textTag'], value

        else:
            return snmprec.SnmprecRecord.formatValue(self, oid, value, **context)


class SnmprecRecord(SnmprecRecordMixIn, snmprec.SnmprecRecord):
    pass


class CompressedSnmprecRecord(SnmprecRecordMixIn,
                              snmprec.CompressedSnmprecRecord):
    pass


# data file types and parsers
RECORD_TYPES = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
    SnmprecRecord.ext: SnmprecRecord(),
    CompressedSnmprecRecord.ext: CompressedSnmprecRecord(),
}

helpMessage = """\
Usage: %s [--help]
    [--version]
    [--quiet]
    [--sort-records]
    [--ignore-broken-records]
    [--deduplicate-records]
    [--escaped-strings]
    [--mib-source=<url>]
    [--start-object=<MIB-NAME::[symbol-name]|OID>]
    [--stop-object=<MIB-NAME::[symbol-name]|OID>]
    [--source-record-type=<%s>]
    [--destination-record-type=<%s>]
    [--input-file=<filename>]
    [--output-file=<filename>]\
""" % (sys.argv[0],
       '|'.join(RECORD_TYPES),
       '|'.join(RECORD_TYPES))

try:
    opts, params = getopt.getopt(
        sys.argv[1:], 'hv',
        ['help', 'version', 'quiet', 'sort-records',
         'ignore-broken-records',
         'deduplicate-records',
         'escaped-strings',
         'start-oid=', 'stop-oid=', 'start-object=',
         'stop-object=',
         'mib-source=', 'source-record-type=',
         'destination-record-type=',
         'input-file=', 'output-file='])

except Exception:
    if verboseFlag:
        sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))

    sys.exit(-1)

if params:
    if verboseFlag:
        sys.stderr.write('ERROR: extra arguments supplied %s\r\n'
                         '%s\r\n' % (params, helpMessage))
    sys.exit(-1)

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  SNMP Simulator data files management and repair tool.
Documentation:
  http://snmplabs.com/snmpsim/managing-data-files.html
%s
""" % helpMessage)
        sys.exit(-1)
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
       sys.version, helpMessage))
        sys.exit(-1)

    if opt[0] == '--quiet':
        verboseFlag = False

    if opt[0] == '--sort-records':
        sortRecords = True

    if opt[0] == '--ignore-broken-records':
        ignoreBrokenRecords = True

    if opt[0] == '--deduplicate-records':
        deduplicateRecords = True

    if opt[0] == '--escaped-strings':
        escapedStrings = True

    # obsolete begin
    if opt[0] == '--start-oid':
        startOID = univ.ObjectIdentifier(opt[1])

    if opt[0] == '--stop-oid':
        stopOID = univ.ObjectIdentifier(opt[1])
    # obsolete end

    if opt[0] == '--mib-source':
        mibSources.append(opt[1])

    if opt[0] == '--start-object':
        startOID = rfc1902.ObjectIdentity(*opt[1].split('::', 1))

    if opt[0] == '--stop-object':
        stopOID = rfc1902.ObjectIdentity(*opt[1].split('::', 1),
                                         **dict(last=True))
    if opt[0] == '--source-record-type':
        if opt[1] not in RECORD_TYPES:
            if verboseFlag:
                sys.stderr.write(
                    'ERROR: unknown record type <%s> (known types are %s)\r\n'
                    '%s\r\n' % (opt[1], ', '.join(RECORD_TYPES),
                                helpMessage))
            sys.exit(-1)

        srcRecordType = opt[1]

    if opt[0] == '--destination-record-type':
        if opt[1] not in RECORD_TYPES:
            if verboseFlag:
                sys.stderr.write(
                    'ERROR: unknown record type <%s> (known types are %s)\r\n%s'
                    '\r\n' % (opt[1], ', '.join(RECORD_TYPES),
                              helpMessage))
            sys.exit(-1)

        dstRecordType = opt[1]

    if opt[0] == '--input-file':
        inputFiles.append(opt[1])

    if opt[0] == '--output-file':
        outputFile = opt[1]

inputFiles = [RECORD_TYPES[srcRecordType].open(x) for x in inputFiles]

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

if not inputFiles:
    inputFiles.append(sys.stdin)

if (isinstance(startOID, rfc1902.ObjectIdentity) or
        isinstance(stopOID, rfc1902.ObjectIdentity)):

    mibBuilder = builder.MibBuilder()

    mibViewController = view.MibViewController(mibBuilder)

    compiler.addMibCompiler(
        mibBuilder, sources=mibSources or defaultMibSources)

    try:
        if isinstance(startOID, rfc1902.ObjectIdentity):
            startOID.resolveWithMib(mibViewController)

        if isinstance(stopOID, rfc1902.ObjectIdentity):
            stopOID.resolveWithMib(mibViewController)

    except PySnmpError:
        sys.stderr.write('ERROR: %s\r\n' % sys.exc_info()[1])
        sys.exit(-1)

recordsList = []

for inputFile in inputFiles:

    if verboseFlag:
        sys.stderr.write(
            '# Input file #%s, processing records from %s till '
            '%s\r\n' % (inputFiles.index(inputFile),
                        startOID or 'the beginning', stopOID or 'the end'))

    lineNo = 0

    while True:
        line, recLineNo, _ = getRecord(inputFile, lineNo)

        if not line:
            break

        if recLineNo != lineNo + 1:
            if verboseFlag:
                sys.stderr.write(
                    '# Losing comment at lines %s..%s (input file #'
                    '%s)\r\n' % (lineNo + 1, recLineNo - 1,
                                 inputFiles.index(inputFile)))

            lineNo = recLineNo

            lostComments += 1

        backdoor = {}

        try:
            oid, value = RECORD_TYPES[srcRecordType].evaluate(line, backdoor=backdoor)

        except error.SnmpsimError:
            if ignoreBrokenRecords:
                if verboseFlag:
                    sys.stderr.write(
                        '# Skipping broken record <%s>: '
                        '%s\r\n' % (line, sys.exc_info()[1]))
                brokenCount += 1
                continue

            else:
                if verboseFlag:
                    sys.stderr.write(
                        'ERROR: broken record <%s>: '
                        '%s\r\n' % (line, sys.exc_info()[1]))

                sys.exit(-1)

        if (startOID and startOID > oid or
                stopOID and stopOID < oid):
            skippedCount += 1
            continue

        recordsList.append((oid, value, backdoor))

if sortRecords:
    recordsList.sort(key=lambda x: x[0])

uniqueIndices = set()

for record in recordsList:
    if deduplicateRecords:
        if record[0] in uniqueIndices:
            if verboseFlag:
                sys.stderr.write('# Skipping duplicate record '
                                 '<%s>\r\n' % record[0])

            duplicateCount += 1

            continue

        else:
            uniqueIndices.add(record[0])

    try:
        outputFile.write(
            RECORD_TYPES[dstRecordType].format(
                record[0], record[1], backdoor=record[2], nohex=escapedStrings
            )
        )

    except Exception:
        sys.stderr.write('ERROR: record not written: %s\r\n' % sys.exc_info()[1])
        break

    writtenCount += 1
    if record[2]:
        variationCount += 1

if verboseFlag:
    sys.stderr.write(
        '# Records: written %s, filtered out %s, de-duplicated %s, ignored '
        '%s, broken %s, variated %s\r\n' % (
            writtenCount, skippedCount, duplicateCount, lostComments,
            brokenCount, variationCount))

outputFile.flush()
outputFile.close()
