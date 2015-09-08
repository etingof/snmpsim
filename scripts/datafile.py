#!/usr/bin/env python
#
# SNMP Simulator data file management tool
#
# Written by Ilya Etingof <ilya@glas.net>, 2011-2015
#
import getopt
import sys
from pyasn1.type import univ
from pysnmp.smi import builder, rfc1902, view, compiler
from snmpsim.record.search.file import getRecord
from snmpsim.record import snmprec, dump, mvc, sap, walk
from snmpsim import error

# Defaults
verboseFlag = True
mibSources = []
defaultMibSources = [ 'http://mibs.snmplabs.com/asn1/@mib@' ]
sortRecords = ignoreBrokenRecords = deduplicateRecords = lostComments = False
startOID = stopOID = None
srcRecordType = dstRecordType = 'snmprec'
inputFiles = []
outputFile = sys.stdout
if hasattr(outputFile, 'buffer'):
    outputFile = outputFile.buffer
writtenCount = skippedCount = duplicateCount = brokenCount = variationCount = 0

class SnmprecRecord(snmprec.SnmprecRecord):
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
            return snmprec.SnmprecRecord.formatValue(self, oid, value)

# data file types and parsers
recordsSet = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
    SnmprecRecord.ext: SnmprecRecord()
}

helpMessage = """\
Usage: %s [--help]
    [--version]
    [--quiet]
    [--sort-records]
    [--ignore-broken-records]
    [--deduplicate-records]
    [--mib-source=<url>]
    [--start-object=<MIB-NAME::[symbol-name]|OID>]
    [--stop-object=<MIB-NAME::[symbol-name]|OID>]
    [--source-record-type=<%s>]
    [--destination-record-type=<%s>]
    [--input-file=<filename>]
    [--output-file=<filename>]""" % (sys.argv[0], 
                                     '|'.join(recordsSet.keys()),
                                     '|'.join(recordsSet.keys()))

try:
    opts, params = getopt.getopt(sys.argv[1:], 'hv',
        ['help', 'version', 'quiet', 'sort-records', 
         'ignore-broken-records', 'deduplicate-records',
         'start-oid=', 'stop-oid=', 'start-object=', 'stop-object=',
         'mib-source=', 'source-record-type=', 'destination-record-type=',
         'input-file=', 'output-file=']
    )
except Exception:
    if verboseFlag:
        sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if params:
    if verboseFlag:
        sys.stderr.write('ERROR: extra arguments supplied %s\r\n%s\r\n' % (params, helpMessage))
    sys.exit(-1)    

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  SNMP Simulator data files management and repair tool.
Documentation:
  http://snmpsim.sourceforge.net/managing-data-files.html
%s
""" % helpMessage)
        sys.exit(-1)
    if opt[0] == '-v' or opt[0] == '--version':
        import snmpsim, pysmi, pysnmp, pyasn1
        sys.stderr.write("""\
SNMP Simulator version %s, written by Ilya Etingof <ilya@glas.net>
Using foundation libraries: pysmi %s, pysnmp %s, pyasn1 %s.
Python interpreter: %s
Software documentation and support at http://snmpsim.sf.net
%s
""" % (snmpsim.__version__, hasattr(pysmi, '__version__') and pysmi.__version__ or 'unknown', hasattr(pysnmp, '__version__') and pysnmp.__version__ or 'unknown', hasattr(pyasn1, '__version__') and pyasn1.__version__ or 'unknown', sys.version, helpMessage))
        sys.exit(-1)
    if opt[0] == '--quiet':
        verboseFlag = False
    if opt[0] == '--sort-records':
        sortRecords = True
    if opt[0] == '--ignore-broken-records':
        ignoreBrokenRecords = True
    if opt[0] == '--deduplicate-records':
        deduplicateRecords = True
    # obsolete begin
    if opt[0] == '--start-oid':
        startOID = univ.ObjectIdentifier(opt[1])
    if opt[0] == '--stop-oid':
        stopOID = univ.ObjectIdentifier(opt[1])
    # obsolete end
    if opt[0] == '--mib-source':
        mibSources.append(opt[1])
    if opt[0] == '--start-object':
        startOID = rfc1902.ObjectIdentity(*opt[1].split('::'))
    if opt[0] == '--stop-object':
        stopOID = rfc1902.ObjectIdentity(*opt[1].split('::'), **dict(last=True))
    if opt[0] == '--source-record-type':
        if opt[1] not in recordsSet:
            if verboseFlag:
                sys.stderr.write('ERROR: unknown record type <%s> (known types are %s)\r\n%s\r\n' % (opt[1], ', '.join(recordsSet.keys()), helpMessage))
            sys.exit(-1)
        srcRecordType = opt[1]
    if opt[0] == '--destination-record-type':
        if opt[1] not in recordsSet:
            if verboseFlag:
                sys.stderr.write('ERROR: unknown record type <%s> (known types are %s)\r\n%s\r\n' % (opt[1], ', '.join(recordsSet.keys()), helpMessage))
            sys.exit(-1)
        dstRecordType = opt[1]
    if opt[0] == '--input-file':
        inputFiles.append(open(opt[1], 'rb'))
    if opt[0] == '--output-file':
        outputFile = open(opt[1], 'wb')

if not inputFiles:
    inputFiles.append(sys.stdin)

if isinstance(startOID, rfc1902.ObjectIdentity) or \
        isinstance(stopOID, rfc1902.ObjectIdentity):
    mibBuilder = builder.MibBuilder()

    mibViewController = view.MibViewController(mibBuilder)

    compiler.addMibCompiler(
        mibBuilder, sources=mibSources or defaultMibSources
    )
    if isinstance(startOID, rfc1902.ObjectIdentity):
        startOID.resolveWithMib(mibViewController)
    if isinstance(stopOID, rfc1902.ObjectIdentity):
        stopOID.resolveWithMib(mibViewController)

recordsList = []

for inputFile in inputFiles:
    if verboseFlag:
        sys.stderr.write('# Input file #%s, processing records from %s till %s\r\n' % (inputFiles.index(inputFile), startOID or 'the beginning', stopOID or 'the end'))
    lineNo = 0
    while True:
        line, recLineNo, _ = getRecord(inputFile, lineNo)
        if not line:
            break
        if recLineNo != lineNo:
            if verboseFlag:
                sys.stderr.write('# Losing comment at line %s (input file #%s)\r\n' % (inputFiles.index(inputFile), recLineNo))
            lineNo = recLineNo
            lostComments += 1
        backdoor = {}
        try:
            oid, value = recordsSet[srcRecordType].evaluate(line, backdoor=backdoor)
        except error.SnmpsimError:
            if ignoreBrokenRecords:
                if verboseFlag:
                    sys.stderr.write('# Skipping broken record <%s>\r\n' % line)
                brokenCount += 1
                continue
            else:
                if verboseFlag:
                    sys.stderr.write('ERROR: broken record <%s>\r\n' % line)
                sys.exit(-1)    

        if startOID and startOID > oid or \
                stopOID and stopOID < oid:
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
                sys.stderr.write('# Skipping duplicate record <%s>\r\n' % record[0])
            duplicateCount += 1
            continue
        else:
            uniqueIndices.add(record[0])
    try:
        outputFile.write(
            recordsSet[dstRecordType].format(
                record[0], record[1], backdoor=record[2]
            )
        )
    except:
        sys.stderr.write('ERROR: record not written: %s\r\n'%sys.exc_info()[1])
        break

    writtenCount += 1
    if record[2]:
        variationCount += 1

if verboseFlag:
    sys.stderr.write(
        '# Records: written %s, filtered out %s, deduped %s, ignored %s, broken %s, variated %s\r\n' % (writtenCount, skippedCount, duplicateCount, lostComments, brokenCount, variationCount)
    )

outputFile.flush()
outputFile.close()
