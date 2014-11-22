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
import time
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.record.snmprec import SnmprecRecord
from snmpsim.mltsplit import split
from snmpsim import error, log
from pysnmp.smi.error import WrongValueError
try:
    from redis import StrictRedis
except ImportError:
    StrictRedis = None

def init(**context):
    options = {}
    if context['options']:
        options.update(
            dict([split(x, ':') for x in split(context['options'], ',')])
        )
    connectParams = dict(
        [ (k,options[k]) for k in options if k in ('host', 'port', 'password', 'db', 'unix_socket') ]
    )
    for k in 'port', 'db':
        if k in connectParams:
            connectParams[k] = int(connectParams[k])
    if not connectParams:
        raise error.SnmpsimError('Redis connect parameters not specified')

    if StrictRedis is None:
        raise error.SnmpsimError('redis-py Python package must be installed!')

    moduleContext['dbConn'] = StrictRedis(**connectParams)
    
    if context['mode'] == 'recording':
        if 'key-spaces-id' in options:
            moduleContext['key-spaces-id'] = int(options['key-spaces-id'])
        else:    
            from random import randrange, seed
            seed()
            moduleContext['key-spaces-id'] = randrange(0, 0xffffffff)

        log.msg('redis: using key-spaces-id %s' % moduleContext['key-spaces-id'])
        
        if 'iterations' in options:
            moduleContext['iterations'] = max(0, int(options['iterations'])-1)
        if 'period' in options:
            moduleContext['period'] = float(options['period'])
        else:
            moduleContext['period'] = 60.0

        redisScript = options.get('evalsha')
        if redisScript:
            log.msg('redis: using server-side script %s' % redisScript)

    elif context['mode'] == 'variating':
        moduleContext['booted'] = time.time()

    moduleContext['ready'] = True


unpackTag = SnmprecRecord().unpackTag

def variate(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    if 'settings' not in recordContext:
        settings = recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])
        if 'key-spaces-id' not in settings:
            log.msg('redis:mandatory key-spaces-id option is missing')
            return context['origOid'], tag, context['errorStatus']

        settings['period'] = float(settings.get('period', 60))

        if 'evalsha' in settings:
            if not dbConn.script_exists(settings['evalsha']):
                log.msg('redis: lua script %s does not exist at Redis' % settings['evalsha'])
                return context['origOid'], tag, context['errorStatus']

        recordContext['ready'] = True

    if 'ready' not in recordContext:
        return context['origOid'], tag, context['errorStatus']

    redisScript = recordContext['settings'].get('evalsha')

    keySpacesId = recordContext['settings']['key-spaces-id']
    if recordContext['settings']['period']:
        keySpaceIdx = int((time.time() - moduleContext['booted']) % (recordContext['settings']['period'] * int(dbConn.llen(keySpacesId))) // recordContext['settings']['period'])
    else:
        keySpaceIdx = 0
    keySpace = dbConn.lindex(keySpacesId, keySpaceIdx)
    if 'current-keyspace' not in recordContext or \
            recordContext['current-keyspace'] != keySpace:
        log.msg('redis: now using keyspace %s (cycling period %s)' % (keySpace, recordContext['settings']['period'] or '<disabled>'))
        recordContext['current-keyspace'] = keySpace

    if keySpace is None:
        return origOid, tag, context['errorStatus']

    origOid = context['origOid']
    dbOid = '.'.join(['%10s' % x for x in str(origOid).split('.')])

    if context['setFlag']:
        if 'hexvalue' in context:
            textTag = context['hextag']
            textValue = context['hexvalue']
        else:
            textTag = SnmprecGrammar().getTagByType(context['origValue'])
            textValue = str(context['origValue'])

        if redisScript:
            prevTagAndValue = dbConn.evalsha(redisScript, 1, keySpace + '-' + dbOid)
        else:
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

        if redisScript:
            dbConn.evalsha(redisScript, 1, keySpace + '-' + dbOid, textTag + '|' + textValue)
        else:
            dbConn.set(keySpace + '-' + dbOid, textTag + '|' + textValue)

        return origOid, textTag, context['origValue']
    else:
        if context['nextFlag']:
            textOid = dbConn.lindex(keySpace + '-oids_ordering',
                                    getNextOid(dbConn, keySpace, dbOid, 
                                               index=True))
        else:
            textOid = keySpace + '-' + dbOid

        if redisScript:
            tagAndValue = dbConn.evalsha(redisScript, 1, textOid)
        else:
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
    while maxlen >= minlen and listsize:
        listsize -= 1
        idx = minlen+(maxlen-minlen)//2
        nextOid = dbConn.lindex(listKey, idx)
        if nextOid < oidKey:
            minlen = idx + 1
        elif nextOid > oidKey:
            maxlen = idx - 1
        else:
            idx += 1
            break
    if not listsize:
        raise error.SnmpsimError('empty/unsorted %s' % listKey)
    return not index and dbConn.lindex(listKey, idx) or idx

def record(oid, tag, value, **context):
    if 'ready' not in moduleContext:
        raise error.SnmpsimError('module not initialized')

    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    if 'started' not in moduleContext:
        moduleContext['started'] = time.time()

    redisScript = moduleContext.get('evalsha')

    keySpace = '%.10d' % (moduleContext['key-spaces-id'] + moduleContext.get('iterations', 0))

    if context['stopFlag']:
        dbConn.sort(keySpace + '-' + 'temp_oids_ordering', store=keySpace + '-' + 'oids_ordering', alpha=True)

        dbConn.delete(keySpace + '-' + 'temp_oids_ordering')
        dbConn.rpush(moduleContext['key-spaces-id'], keySpace)
        log.msg('redis: done with key-space %s' % keySpace)
        if 'iterations' in moduleContext and moduleContext['iterations']:
            log.msg('redis: %s iterations remaining' % moduleContext['iterations'])
            moduleContext['started'] = time.time()
            moduleContext['iterations'] -= 1
            wait = max(0, moduleContext['period'] - (time.time() - moduleContext['started']))

            raise error.MoreDataNotification(period=wait)
        else:
            raise error.NoDataNotification()

    dbOid = '.'.join(['%10s' % x for x in oid.split('.')])
    if 'hexvalue' in context:
        textTag = context['hextag']
        textValue = context['hexvalue']
    else:
        textTag = SnmprecGrammar().getTagByType(context['origValue'])
        textValue = str(context['origValue'])

    dbConn.lpush(keySpace + '-temp_oids_ordering', keySpace + '-' + dbOid)
    if redisScript:
        dbConn.evalsha(redisScript, 1, keySpace + '-' + dbOid, textTag + '|' + textValue)
    else:
        dbConn.set(keySpace + '-' + dbOid, textTag + '|' + textValue)

    if not context['count']:
        settings = {
            'key-spaces-id': moduleContext['key-spaces-id']
        }
        if 'period' in moduleContext:
            settings['period'] = '%.2f' % float(moduleContext['period'])
        if 'addon' in moduleContext:
            settings.update(
                dict([split(x, '=') for x in moduleContext['addon']])
            )
        value = ','.join([ '%s=%s' % (k,v) for k,v in settings.items() ])
        return str(context['startOID']), ':redis', value
    else:
        raise error.NoDataNotification()

def shutdown(**context):
    if 'dbConn' in moduleContext: moduleContext.pop('dbConn')
