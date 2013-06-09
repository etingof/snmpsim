#!/usr/bin/env python
#
# SNMP Simulator MIB to data file converter
#
# Written by Ilya Etingof <ilya@glas.net>, 2011-2013
#
import getopt
import sys
import random
from pyasn1.type import univ
from pyasn1.error import PyAsn1Error
from pysnmp.smi import builder, view, error
from pysnmp.proto import rfc1902
from pysnmp import debug
from snmpsim.record import snmprec

# Defaults
verboseFlag = True
startOID = stopOID = None
outputFile = sys.stderr
stringPool = 'Portez ce vieux whisky au juge blond qui fume!'.split()
counterRange = (0, 0xffffffff)
counter64Range = (0, 0xffffffffffffffff)
gaugeRange = (0, 0xffffffff)
timeticksRange = (0, 0xffffffff)
unsignedRange = (0, 65535)
int32Range = (0, 32)  # these values are more likely to fit constraints
automaticValues = 5000
tableSize = 10
modNames = []
mibDirs = []

helpMessage = """Usage: %s [--help]
    [--version]
    [--debug=<%s>]
    [--quiet]
    [--pysnmp-mib-dir=<path>] [--mib-module=<name>]
    [--start-oid=<OID>] [--stop-oid=<OID>]
    [--manual-values]
    [--automatic-values=<max-probes>]
    [--table-size=<number>]
    [--output-file=<filename>]
    [--string-pool=<words>]
    [--counter-range=<min,max>]
    [--counter64-range=<min,max>]
    [--gauge-range=<min,max>]
    [--timeticks-range=<min,max>]
    [--unsigned-range=<min,max>]
    [--integer32-range=<min,max>]""" % (
        sys.argv[0], 
        '|'.join([ x for x in debug.flagMap.keys() if x not in ('app', 'msgproc', 'proxy', 'io', 'secmod', 'dsp', 'acl') ])
    )

try:
    opts, params = getopt.getopt(sys.argv[1:], 'hv',
        ['help', 'version', 'debug=', 'quiet', 'pysnmp-mib-dir=', 'mib-module=', 'start-oid=', 'stop-oid=', 'manual-values', 'automatic-values=', 'table-size=', 'output-file=', 'string-pool=', 'integer32-range=', 'counter-range=', 'counter64-range=', 'gauge-range=', 'unsigned-range=', 'timeticks-range=']
        )
except Exception:
    sys.stdout.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
    sys.exit(-1)

if params:
    sys.stdout.write('ERROR: extra arguments supplied %s\r\n%s\r\n' % (params, helpMessage))
    sys.exit(-1)    

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  Converts MIB modules into SNMP Simulator data files.
  Takes MIB module in PySNMP format and produces data file for SNMP Simulator
  to playback. Chooses random values or can ask for them interactively.
  Able to fill SNMP conceptual tables with consistent indices.
Documentation:
  http://snmpsim.sourceforge.net/simulation-based-on-mibs.html
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
    if opt[0] == '--debug':
        debug.setLogger(debug.Debug(opt[1]))
    if opt[0] == '--quiet':
        verboseFlag = False
    if opt[0] == '--pysnmp-mib-dir':
        mibDirs.append(opt[1])
    if opt[0] == '--mib-module':
        modNames.append(opt[1])
    if opt[0] == '--start-oid':
        startOID = univ.ObjectIdentifier(opt[1])
    if opt[0] == '--stop-oid':
        stopOID = univ.ObjectIdentifier(opt[1])
    if opt[0] == '--manual-values':
        automaticValues = 0
    if opt[0] == '--automatic-values':
        try:
            automaticValues = int(opt[1])
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)   
    if opt[0] == '--table-size':
        try:
            tableSize = int(opt[1])
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)   
    if opt[0] == '--output-file':
        outputFile = open(opt[1], 'wb')
    if opt[0] == '--string-pool':
        stringPool = opt[1].split()
    if opt[0] == '--counter-range':
        try:
            counterRange = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)
    if opt[0] == '--counter64-range':
        try:
            counter64Range = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)
    if opt[0] == '--gauge-range':
        try:
            gaugeRange = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)
    if opt[0] == '--timeticks-range':
        try:
            timeticksRange = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)
    if opt[0] == '--integer32-range':
        try:
            int32Range = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)
    if opt[0] == '--unsigned-range':
        try:
            unsignedRange = [int(x) for x in opt[1].split(',')]
        except ValueError:
            sys.stdout.write('ERROR: bad value %s: %s\r\n' % (opt[1], sys.exc_info()[1]))
            sys.exit(-1)


# Catch missing params
if not modNames:
    sys.stdout.write('ERROR: MIB modules not specified\r\n%s\r\n' % helpMessage)
    sys.exit(-1)    

def getValue(syntax, hint='', automaticValues=automaticValues):
    # Optionally approve chosen value with the user
    makeGuess = automaticValues
    val = None
    while 1:
        if makeGuess:
            # Pick a value
            if isinstance(syntax, rfc1902.IpAddress):
                val = '.'.join(
                    [ str(random.randrange(1, 256)) for x in range(4) ]
                )
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
                val = ' '.join(
                    [ stringPool[i] for i in range(random.randrange(0, len(stringPool)), random.randrange(0, len(stringPool))) ]
                )
            elif isinstance(syntax, univ.ObjectIdentifier):
                val = '.'.join(['1','3','6','1','3'] + ['%d' % random.randrange(0, 255) for x in range(random.randrange(0, 10))])
            elif isinstance(syntax, rfc1902.Bits):
                val = [random.randrange(0, 256) for x in range(random.randrange(0,9))]
            else:
                val = '?'

        try:
            return syntax.clone(val)
        except PyAsn1Error:
            if makeGuess == 1:
                sys.stdout.write(
                    '*** Inconsistent value: %s\r\n*** See constraints and suggest a better one for:\r\n' % (sys.exc_info()[1],)
                )
            if makeGuess:
                makeGuess -= 1
                continue

        sys.stdout.write(
            '%s# Value [\'%s\'] ? ' % (hint,(val is None and '<none>' or val),)
            )
        sys.stdout.flush()
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

# Data file builder

dataFileHandler = snmprec.SnmprecRecord()

mibBuilder = builder.MibBuilder()

mibBuilder.setMibSources(
    *mibBuilder.getMibSources() + tuple(
      [ builder.ZipMibSource(m).init() for m in mibDirs ]
    )
)

# Load MIB tree foundation classes
( MibScalar,
  MibTable,
  MibTableRow,
  MibTableColumn ) = mibBuilder.importSymbols(
    'SNMPv2-SMI',
    'MibScalar',
    'MibTable',
    'MibTableRow',
    'MibTableColumn'
    )

mibView = view.MibViewController(mibBuilder)

output = []

# MIBs walk
for modName in modNames:
    if verboseFlag:
        sys.stdout.write('# MIB module: %s\r\n' % modName)
    mibBuilder.loadModules(modName)
    modOID = oid = univ.ObjectIdentifier(
        mibView.getFirstNodeName(modName)[0]
        )
    rowOID = None
    while modOID.isPrefixOf(oid):
        try:
            oid, label, _ = mibView.getNextNodeName(oid)
        except error.NoSuchObjectError:
            break

        if rowOID and not rowOID.isPrefixOf(oid):
            thisTableSize += 1
            if automaticValues:
                if thisTableSize < tableSize:
                    oid = tuple(rowOID)
                    if verboseFlag:
                        sys.stdout.write('# Synthesizing row #%d of table %s\r\n' % (thisTableSize, rowOID))
                else:
                    if verboseFlag:
                        sys.stdout.write('# Finished table %s (%d rows)\r\n' % (rowOID, thisTableSize))
                    rowOID = None
            else:
                while 1:
                    sys.stdout.write(
                        '# Synthesize row #%d for table %s (y/n)? ' % (thisTableSize, rowOID)
                    )
                    sys.stdout.flush()
                    line = sys.stdin.readline().strip()
                    if line:
                        if line[0] in ('y', 'Y'):
                            oid = tuple(rowOID)
                            break
                        elif line[0] in ('n', 'N'):
                            if verboseFlag:
                                sys.stdout.write('# Finished table %s (%d rows)\r\n' % (rowOID, thisTableSize))
                            rowOID = None
                            break

        if startOID and oid < startOID:
            continue # skip on premature OID
        if stopOID and oid > stopOID:
            break  # stop on out of range condition
 
        mibName, symName, _ = mibView.getNodeLocation(oid)
        node, = mibBuilder.importSymbols(mibName, symName)
    
        if isinstance(node, MibTable):
            hint = '# Table %s::%s\r\n' % (mibName, symName)
            if verboseFlag:
                sys.stdout.write('# Starting table %s::%s (%s)\r\n' % (mibName, symName, univ.ObjectIdentifier(oid)))
            continue
        elif isinstance(node, MibTableRow):
            rowIndices = {}
            suffix = ()
            rowHint = hint + '# Row %s::%s\r\n' % (mibName, symName)
            for impliedFlag, idxModName, idxSymName in node.getIndexNames():
                idxNode, = mibBuilder.importSymbols(idxModName, idxSymName)
                rowHint += '# Index %s::%s (type %s)\r\n' % (idxModName, idxSymName, idxNode.syntax.__class__.__name__)
                rowIndices[idxNode.name] = getValue(idxNode.syntax, verboseFlag and rowHint or '')
                suffix = suffix + node.getAsName(rowIndices[idxNode.name], impliedFlag)
            if rowOID is None:
                thisTableSize = 0
            rowOID = univ.ObjectIdentifier(oid)
            continue
        elif isinstance(node, MibTableColumn):
            oid = node.name
            if oid in rowIndices:
                val = rowIndices[oid]
            else:
                val = getValue(node.syntax, verboseFlag and rowHint + '# Column %s::%s (type %s)\r\n' % (mibName, symName, node.syntax.__class__.__name__) or '')
        elif isinstance(node, MibScalar):
            oid = node.name
            suffix = (0,)
            val = getValue(node.syntax, verboseFlag and '# Scalar %s::%s (type %s)\r\n' % (mibName, symName, node.syntax.__class__.__name__) or '')
        else:
            continue
  
        output.append((oid + suffix, val))
    
    output.sort(
        key=lambda x: univ.ObjectIdentifier(x[0])
    )

    unique = set()

    for oid, val in output:
        if oid in unique:
            if verboseFlag:
                sys.stdout.write(
                    '# Dropping duplicate OID %s\r\n' % (univ.ObjectIdentifier(oid),)
                )
        else:
            outputFile.write(
                dataFileHandler.format(oid, val)
            )
            unique.add(oid)

    if verboseFlag:
        sys.stdout.write(
            '# End of %s, %s OID(s) dumped\r\n' % (modName, len(unique))
        )
