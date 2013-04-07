#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a live Agent using
# a series of snapshots.
#
import os, sys, time, bisect
from pyasn1.type import univ
from pyasn1.compat.octets import str2octs
from snmpsim.record.snmprec import SnmprecRecord
from snmpsim.record.search.file import searchRecordByOid
from snmpsim.record.search.database import RecordIndex
from snmpsim import confdir
from snmpsim import error

settingsCache = {}
moduleOptions = {}
moduleContext = { 'ready': False }

def init(snmpEngine, **context):
    if context['options']:
        for k,v in [x.split(':') for x in context['options'].split(',')]:
            if k == 'addon':
                if k in moduleOptions:
                    moduleOptions[k].append(v)
                else:
                    moduleOptions[k] = [v]
            else:
                moduleOptions[k] = v
    if context['mode'] == 'variating':
        moduleContext['booted'] = time.time()
    elif context['mode'] == 'recording':
        if 'dir' not in moduleOptions:
            raise error.SnmpsimError('SNMP snapshots directory not specified')
        if not os.path.exists(moduleOptions['dir']):
            sys.stdout.write('\r\nmultiplex: creating %s...\r\n' % moduleOptions['dir'])
            os.makedirs(moduleOptions['dir'])
        if 'iterations' in moduleOptions:
            moduleOptions['iterations'] = int(moduleOptions['iterations'])
        if 'period' in moduleOptions:
            moduleOptions['period'] = float(moduleOptions['period'])
        else:
            moduleOptions['period'] = 10.0

    moduleContext['ready'] = True

def variate(oid, tag, value, **context):
    if oid not in settingsCache:
        settingsCache[oid] = dict([ x.split('=') for x in value.split(',') ])
        if 'dir' in settingsCache[oid]:
            settingsCache[oid]['dir'] = settingsCache[oid]['dir'].replace(
                '/', os.path.sep
            )
            if settingsCache[oid]['dir'][0] != os.path.sep:
                for x in confdir.data:
                    d = os.path.join(x, settingsCache[oid]['dir'])
                    if os.path.exists(d):
                        break
                else:
                    sys.stdout.write('multiplex: directory %s not found\r\n' % settingsCache[oid]['dir'])
                    return context['origOid'], tag, context['errorStatus']
            else:
                d = settingsCache[oid]['dir']
            settingsCache[oid]['dirmap'] = dict(
                [ (int(os.path.basename(x).split(os.path.extsep)[0]), os.path.join(d, x)) for x in os.listdir(d) if x[-7:] == 'snmprec' ]
            )
            settingsCache[oid]['keys'] = list(
                settingsCache[oid]['dirmap'].keys()
            )
            settingsCache[oid]['bounds'] = (
                min(settingsCache[oid]['keys']), max(settingsCache[oid]['keys'])
            )
        else:
            sys.stdout.write('multiplex: snapshot directory not specified\r\n')
            return context['origOid'], tag, context['errorStatus']
        if 'period' in settingsCache[oid]:
            settingsCache[oid]['period'] = float(settingsCache[oid]['period'])
        else:
            settingsCache[oid]['period'] = 60.0
        if 'wrap' in settingsCache[oid]:
            settingsCache[oid]['wrap'] = bool(settingsCache[oid]['wrap'])
        else:
            settingsCache[oid]['wrap'] = False

        settingsCache[oid]['ready'] = True

    if context['setFlag']:
        return context['origOid'], tag, context['errorStatus']

    if 'ready' not in settingsCache[oid]:
        return context['origOid'], tag, context['errorStatus']

    timeslot = (time.time() - moduleContext['booted']) % (settingsCache[oid]['period'] * len(settingsCache[oid]['dirmap']))
    fileslot = int(timeslot / settingsCache[oid]['period']) + settingsCache[oid]['bounds'][0]

    fileno = bisect.bisect(settingsCache[oid]['keys'], fileslot) - 1

    if 'fileno' not in moduleContext or \
            moduleContext['fileno'] < fileno or \
            settingsCache[oid]['wrap']:
        moduleContext['fileno'] = fileno

    datafile = settingsCache[oid]['dirmap'][
        settingsCache[oid]['keys'][moduleContext['fileno']]
    ]

    if 'datafile' not in moduleContext or \
            moduleContext['datafile'] != datafile:
        if 'datafileobj' in moduleContext:
            moduleContext['datafileobj'].close()
        moduleContext['datafileobj'] = RecordIndex(
            datafile, SnmprecRecord()
        ).create()
        moduleContext['datafile'] = datafile
        
    text, db = moduleContext['datafileobj'].getHandles()

    textOid = str(univ.OctetString('.'.join([ '%s' % x for x in context['origOid']])))

    try:
        line = moduleContext['datafileobj'].lookup(textOid)
    except KeyError:
        offset = searchRecordByOid(context['origOid'], text, SnmprecRecord())
        exactMatch = False
    else:
        offset, subtreeFlag, prevOffset = line.split(str2octs(','))
        exactMatch = True

    text.seek(int(offset))

    line = text.readline()  # matched line

    if context['nextFlag']:
        if exactMatch:
            line = text.readline()
    else:
        if not exactMatch:
            return context['origOid'], tag, context['errorStatus']

    if not line:
        return context['origOid'], tag, context['errorStatus']

    try:
        oid, value = SnmprecRecord().evaluate(line)
    except error.SnmpsimError:
        oid, value = context['origOid'], tag, context['errorStatus']

    return oid, tag, value

def record(oid, tag, value, **context):
    if not moduleContext['ready']:
        raise error.SnmpsimError('module not initialized')
    if 'started' not in moduleContext:
        moduleContext['started'] = time.time()
    if context['stopFlag']:
        if 'file' in moduleContext:
            moduleContext['file'].close()
            del moduleContext['file']
        else:
            moduleContext['filenum'] = 0
        if 'iterations' in moduleOptions and moduleOptions['iterations']:
            wait = max(0, moduleOptions['period'] - (time.time() - moduleContext['started']))
            while wait > 0:
                sys.stdout.write('multiplex: waiting %.2f sec(s), %s OIDs dumped, %s iterations remaining...\r' % (wait, context['total']+context['count'], moduleOptions['iterations']))
                sys.stdout.flush()
                time.sleep(1)
                wait -= 1
            sys.stdout.write(' ' * 77 + '\r')
            moduleContext['started'] = time.time()
            moduleOptions['iterations'] -= 1
            moduleContext['filenum'] += 1
            raise error.MoreDataNotification()
        else:
            raise error.NoDataNotification()

    if 'file' not in moduleContext:
        if 'filenum' not in moduleContext:
            moduleContext['filenum'] = 0
        snmprecfile = os.path.join(moduleOptions['dir'],
                                   '%.5d%ssnmprec' % (moduleContext['filenum'],
                                                      os.path.extsep))
        moduleContext['file'] = open(snmprecfile, 'wb')
        sys.stdout.write('multiplex: writing into %s file...\r\n' % snmprecfile)

    moduleContext['file'].write(
        SnmprecRecord().format(context['origOid'], context['origValue'])
    )

    if not context['count']:
        settings = {
            'dir': moduleOptions['dir'].replace(os.path.sep, '/')
        }
        if 'period' in moduleOptions:
            settings['period'] = '%.2f' % float(moduleOptions['period'])
        if 'addon' in moduleOptions:
            settings.update(
                dict([x.split('=') for x in moduleOptions['addon']])
            )
        value = ','.join([ '%s=%s' % (k,v) for k,v in settings.items() ])
        return str(context['startOID']), ':multiplex', value
    else:
        raise error.NoDataNotification()

def shutdown(snmpEngine, **context): pass
