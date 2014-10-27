#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a live Agent using
# a series of snapshots.
#
import os, sys, time, bisect
from pyasn1.compat.octets import str2octs
from pysnmp.proto import rfc1902
from snmpsim.record.snmprec import SnmprecRecord
from snmpsim.record.search.file import searchRecordByOid, getRecord
from snmpsim.record.search.database import RecordIndex
from snmpsim import confdir
from snmpsim.mltsplit import split
from snmpsim import log
from snmpsim import error

def init(**context):
    if context['options']:
        for k,v in [split(x, ':') for x in split(context['options'], ',')]:
            if k == 'addon':
                if k in moduleContext:
                    moduleContext[k].append(v)
                else:
                    moduleContext[k] = [v]
            else:
                moduleContext[k] = v
    if context['mode'] == 'variating':
        moduleContext['booted'] = time.time()
    elif context['mode'] == 'recording':
        if 'dir' not in moduleContext:
            raise error.SnmpsimError('SNMP snapshots directory not specified')
        if not os.path.exists(moduleContext['dir']):
            log.msg('multiplex: creating %s...' % moduleContext['dir'])
            os.makedirs(moduleContext['dir'])
        if 'iterations' in moduleContext:
            moduleContext['iterations'] = max(0, int(moduleContext['iterations'])-1)
        if 'period' in moduleContext:
            moduleContext['period'] = float(moduleContext['period'])
        else:
            moduleContext['period'] = 10.0

    moduleContext['ready'] = True

def variate(oid, tag, value, **context):
    if 'settings' not in recordContext:
        recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])
        if 'dir' not in recordContext['settings']:
            log.msg('multiplex: snapshot directory not specified')
            return context['origOid'], tag, context['errorStatus']

        recordContext['settings']['dir'] = recordContext['settings']['dir'].replace(
            '/', os.path.sep
        )
        if recordContext['settings']['dir'][0] != os.path.sep:
            for x in confdir.data:
                d = os.path.join(x, recordContext['settings']['dir'])
                if os.path.exists(d):
                    break
            else:
                log.msg('multiplex: directory %s not found' % recordContext['settings']['dir'])
                return context['origOid'], tag, context['errorStatus']
        else:
            d = recordContext['settings']['dir']
        recordContext['dirmap'] = dict(
            [ (int(os.path.basename(x).split(os.path.extsep)[0]), os.path.join(d, x)) for x in os.listdir(d) if x[-7:] == 'snmprec' ]
        )
        recordContext['keys'] = list(
            recordContext['dirmap'].keys()
        )
        recordContext['bounds'] = (
            min(recordContext['keys']), max(recordContext['keys'])
        )
        if 'period' in recordContext['settings']:
            recordContext['settings']['period'] = float(recordContext['settings']['period'])
        else:
            recordContext['settings']['period'] = 60.0
        if 'wrap' in recordContext['settings']:
            recordContext['settings']['wrap'] = bool(recordContext['settings']['wrap'])
        else:
            recordContext['settings']['wrap'] = False
        if 'control' in recordContext['settings']:
            recordContext['settings']['control'] = rfc1902.ObjectName(
                recordContext['settings']['control']
            )
            log.msg('multiplex: using control OID %s for subtree %s, time-based multiplexing disabled' % (recordContext['settings']['control'], oid))

        recordContext['ready'] = True

    if 'ready' not in recordContext:
        return context['origOid'], tag, context['errorStatus']

    if oid not in moduleContext:
        moduleContext[oid] = {}

    if context['setFlag']:
        if 'control' in recordContext['settings'] and \
                recordContext['settings']['control'] == context['origOid']:
            fileno = int(context['origValue'])
            if fileno >= len(recordContext['keys']):
                log.msg('multiplex: .snmprec file number %s over limit of %s' % (fileno, len(recordContext['keys'])))
                return context['origOid'], tag, context['errorStatus']
            moduleContext[oid]['fileno'] = fileno
            log.msg('multiplex: switched to file #%s (%s)' % (recordContext['keys'][fileno], recordContext['dirmap'][recordContext['keys'][fileno]]))
            return context['origOid'], tag, context['origValue']
        else:
            return context['origOid'], tag, context['errorStatus']

    if 'control' in recordContext['settings']:
        if 'fileno' not in moduleContext[oid]:
            moduleContext[oid]['fileno'] = 0
        if not context['nextFlag'] and \
                recordContext['settings']['control'] == context['origOid']:
            return context['origOid'], tag, rfc1902.Integer32(moduleContext[oid]['fileno'])
    else:
        timeslot = (time.time() - moduleContext['booted']) % (recordContext['settings']['period'] * len(recordContext['dirmap']))
        fileslot = int(timeslot / recordContext['settings']['period']) + recordContext['bounds'][0]

        fileno = bisect.bisect(recordContext['keys'], fileslot) - 1

        if 'fileno' not in moduleContext[oid] or \
                moduleContext[oid]['fileno'] < fileno or \
                recordContext['settings']['wrap']:
            moduleContext[oid]['fileno'] = fileno

    datafile = recordContext['dirmap'][
        recordContext['keys'][moduleContext[oid]['fileno']]
    ]

    if 'datafile' not in moduleContext[oid] or \
            moduleContext[oid]['datafile'] != datafile:
        if 'datafileobj' in moduleContext[oid]:
            moduleContext[oid]['datafileobj'].close()
        moduleContext[oid]['datafileobj'] = RecordIndex(
            datafile, SnmprecRecord()
        ).create()
        moduleContext[oid]['datafile'] = datafile

        log.msg('multiplex: switching to data file %s for %s' % (datafile, context['origOid']))
        
    text, db = moduleContext[oid]['datafileobj'].getHandles()

    textOid = str(rfc1902.OctetString('.'.join([ '%s' % x for x in context['origOid']])))

    try:
        line = moduleContext[oid]['datafileobj'].lookup(textOid)
    except KeyError:
        offset = searchRecordByOid(context['origOid'], text, SnmprecRecord())
        exactMatch = False
    else:
        offset, subtreeFlag, prevOffset = line.split(str2octs(','))
        exactMatch = True

    text.seek(int(offset))

    line, _, _ = getRecord(text)  # matched line

    if context['nextFlag']:
        if exactMatch:
            line, _, _ = getRecord(text)
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
    if 'ready' not in moduleContext:
        raise error.SnmpsimError('module not initialized')
    if 'started' not in moduleContext:
        moduleContext['started'] = time.time()
    if context['stopFlag']:
        if 'file' in moduleContext:
            moduleContext['file'].close()
            del moduleContext['file']
        else:
            moduleContext['filenum'] = 0
        if 'iterations' in moduleContext and moduleContext['iterations']:
            log.msg('multiplex: %s iterations remaining' % moduleContext['iterations'])
            moduleContext['started'] = time.time()
            moduleContext['iterations'] -= 1
            moduleContext['filenum'] += 1
            wait = max(0, moduleContext['period'] - (time.time() - moduleContext['started']))
            raise error.MoreDataNotification(period=wait)
        else:
            raise error.NoDataNotification()

    if 'file' not in moduleContext:
        if 'filenum' not in moduleContext:
            moduleContext['filenum'] = 0
        snmprecfile = os.path.join(moduleContext['dir'],
                                   '%.5d%ssnmprec' % (moduleContext['filenum'],
                                                      os.path.extsep))
        moduleContext['file'] = open(snmprecfile, 'wb')
        log.msg('multiplex: writing into %s file...' % snmprecfile)

    moduleContext['file'].write(
        SnmprecRecord().format(context['origOid'], context['origValue'])
    )

    if not context['total']:
        settings = {
            'dir': moduleContext['dir'].replace(os.path.sep, '/')
        }
        if 'period' in moduleContext:
            settings['period'] = '%.2f' % float(moduleContext['period'])
        if 'addon' in moduleContext:
            settings.update(
                dict([split(x, '=') for x in moduleContext['addon']])
            )
        value = ','.join([ '%s=%s' % (k,v) for k,v in settings.items() ])
        return str(context['startOID']), ':multiplex', value
    else:
        raise error.NoDataNotification()

def shutdown(**context): pass
