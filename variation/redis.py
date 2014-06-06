#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a writable Agent using
# noSQL backend (Redis) for storing Managed Objects
#
# Module initialization parameters are host:<redis-host>,port:<redis-port>,db:<redis-db> 
#
# Uses the following data layout:
# Redis LIST type containing sorted OIDs. This is used for answering 
# GETNEXT/GETBULK type queries
# Redis HASH type containing OID-value pairs
# For successful operation each managed OID must be present in both
# data structures
#
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.record.snmprec import SnmprecRecord
from snmpsim import error, log
from pysnmp.smi.error import WrongValueError
try:
    from redis import StrictRedis
except ImportError:
    raise error.SnmpsimError('Redis module for Python must be installed!')

def init(**context):
    options = {}
    if context['options']:
        options.update(
            dict([x.split(':') for x in context['options'].split(',')])
        )
    connectParams = dict(
        [ (k,options[k]) for k in options if k in ('host', 'port', 'password', 'db''unix_socket') ]
    )
    for k in 'port', 'db':
        if k in connectParams:
            connectParams[k] = int(connectParams[k])
    if not connectParams:
        raise error.SnmpsimError('Redis connect parameters not specified')

    moduleContext['dbConn'] = StrictRedis(**connectParams)
    
    if context['mode'] == 'recording':
        if 'key-space' in options:
            moduleContext['keySpace'] = options['key-space']
        else:    
            from random import randrange, seed
            seed()
            moduleContext['keySpace'] = '%.10d' % randrange(0, 0xffffffff)

        log.msg('Using key-space ID %s' % moduleContext['keySpace'])

unpackTag = SnmprecRecord().unpackTag

def variate(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    if 'key-spaces' not in recordContext:
        options = dict([ [kv for kv in token.split(':')] for token in value.split(',')])
        if 'key-spaces' not in options:
            log.msg('mandatory key-spaces option is missing')
            return context['origOid'], tag, context['errorStatus']
    
        keySpaces = options['key-spaces'].split(';')

        recordContext['key-spaces'] = keySpaces
    else:
        keySpaces = recordContext['key-spaces']

    keySpace = keySpaces[0] # XXX

    origOid = context['origOid']
    dbOid = '.'.join(['%10s' % x for x in str(origOid).split('.')])

    if context['setFlag']:
        if 'hexvalue' in context:
            textTag = context['hextag']
            textValue = context['hexvalue']
        else:
            textTag = SnmprecGrammar().getTagByType(context['origValue'])
            textValue = str(context['origValue'])

        prevTagAndValue = dbConn.get(keySpace + '-' + dbOid)
        if prevTagAndValue:
            prevTag, prevValue = prevTagAndValue.split('|')
            if unpackTag(prevTag)[0] != unpackTag(textTag)[0]:
                raise WrongValueError(name=origOid, idx=max(0, context['varsTotal']-context['varsRemaining']-1))
        else:
            dbConn.linsert(keySpace + '-oids_ordering',
                           'after',
                           getNextOid(dbConn, keySpace, dbOid),
                           dbOid)

        dbConn.set(keySpace + '-' + dbOid, textTag + '|' + textValue)

        return origOid, textTag, context['origValue']
    else:
        if context['nextFlag']:
            textOid = dbConn.lindex(keySpace + '-oids_ordering',
                                    getNextOid(dbConn, keySpace, dbOid, 
                                               index=True))
        else:
            textOid = keySpace + '-' + dbOid
        
        tagAndValue = dbConn.get(textOid)

        if not tagAndValue:
            return origOid, tag, context['errorStatus']

        textOid = '.'.join([x.strip() for x in textOid.split('-', 1)[1].split('.')])
        textTag, textValue = tagAndValue.split('|', 1)

        return textOid, textTag, textValue

def getNextOid(dbConn, keySpace, dbOid, index=False):
    listKey = keySpace + '-oids_ordering'
    oidKey = keySpace + '-' + dbOid
    maxlen = listsize = dbConn.llen(listKey)
    minlen = 0
    while maxlen >= minlen:
        idx = minlen+(maxlen-minlen)//2
        nextOid = dbConn.lindex(listKey, idx)
        if nextOid < oidKey:
            minlen = idx + 1
        elif nextOid > oidKey:
            maxlen = idx - 1
        else:
            idx += 1
            break
    return not index and dbConn.lindex(listKey, idx) or idx

def record(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    if context['stopFlag']:
        raise error.NoDataNotification()

    keySpace = moduleContext['keySpace']

    dbOid = '.'.join(['%10s' % x for x in oid.split('.')])
    if 'hexvalue' in context:
        textTag = context['hextag']
        textValue = context['hexvalue']
    else:
        textTag = SnmprecGrammar().getTagByType(context['origValue'])
        textValue = str(context['origValue'])

    dbConn.lpush(keySpace + '-temp_oids_ordering', keySpace + '-' + dbOid)
    dbConn.set(keySpace + '-' + dbOid, textTag + '|' + textValue)

    if not context['count']:
        return str(context['startOID']), ':redis', 'key-spaces:%s' % keySpace
    else:
        raise error.NoDataNotification()

def shutdown(**context):
    dbConn = moduleContext.pop('dbConn', None)
    if dbConn:
        if 'mode' in context and context['mode'] == 'recording':
            keySpace = moduleContext['keySpace']
            dbConn.sort(keySpace + '-' + 'temp_oids_ordering', store=keySpace + '-' + 'oids_ordering', alpha=True)

            dbConn.delete(keySpace + '-' + 'temp_oids_ordering')
