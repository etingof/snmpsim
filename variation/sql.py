#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a writable Agent using
# SQL backend for storing Managed Objects
#
# Module initialization parameters are dbtype:<dbms>,dboptions:<options>
#
# Expects to work a table of the following layout:
# CREATE TABLE <tablename> (oid text primary key, tag text, value text,
#                           maxaccess text default "read-only")
#
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim import error

dbConn = None
dbTable = 'snmprec'

def init(snmpEngine, **context):
    global dbConn, dbTable
    options = {}
    if context['options']:
        options.update(
            dict([x.split(':') for x in context['options'].split(',')])
        )
    if 'dbtype' not in options:
        raise error.SnmpsimError('database type not specified')
    db = __import__(options['dbtype'])
    if 'dboptions' not in options:
        raise error.SnmpsimError('database connect options not specified')
    dbConn = db.connect(*options['dboptions'].split('@'))
    if 'dbtable' in options:
        dbTable = options['dbtable']
    if 'mode' in context and context['mode'] == 'recording':
        cursor = dbConn.cursor()
        try:
            cursor.execute('select * from %s' % dbTable)
        except:
            cursor.execute('CREATE TABLE %s (oid text primary key, tag text, value text, maxaccess text default "read-only")' % dbTable)
        cursor.close()

def variate(oid, tag, value, **context):
    if dbConn is None:
        raise error.SnmpsimError('variation module not initialized')

    cursor = dbConn.cursor()

    dbTable, = value.split(',')

    origOid = context['origOid']
    sqlOid = '.'.join(['%10s' % x for x in str(origOid).split('.')])

    if context['setFlag']:
        if 'hexvalue' in context:
            textTag = context['hextag']
            textValue = context['hexvalue']
        else:
            textTag = SnmprecGrammar().getTagByType(context['origValue'])
            textValue = str(context['origValue'])
        cursor.execute(
            'select maxaccess,tag from %s where oid=?' % dbTable, (sqlOid,)
        )
        resultset = cursor.fetchone()
        if resultset:
            maxaccess = resultset[0]
            if maxaccess != 'read-write':
                return origOid, tag, context['errorStatus']
            cursor.execute(
                'update %s set tag=?,value=? where oid=?' % dbTable, (textTag, textValue, sqlOid)
            )
        else:
            cursor.execute(
                'insert into %s values (?, ?, ?, "read-write")' % dbTable, (sqlOid, textTag, textValue)
            )
        if context['varsRemaining'] == 0:  # last OID in PDU
            dbConn.commit()
        cursor.close()
        return origOid, textTag, context['origValue']
    else:
        if context['nextFlag']:
            cursor.execute('select oid from %s where oid>? order by oid limit 1' % dbTable, (sqlOid,))
            resultset = cursor.fetchone()
            if resultset:
                origOid = origOid.clone(
                  '.'.join([x.strip() for x in str(resultset[0]).split('.')])
                )
                sqlOid = '.'.join(['%10s' % x for x in str(origOid).split('.')])
            else:
                cursor.close()
                return origOid, tag, context['errorStatus']

        cursor.execute('select tag, value from %s where oid=?' % dbTable, (sqlOid,))
        resultset = cursor.fetchone()
        cursor.close()

        if resultset:
            return origOid, str(resultset[0]), str(resultset[1])
        else:
            return origOid, tag, context['errorStatus']

def record(oid, tag, value, **context):
    if dbConn is None:
        raise error.SnmpsimError('variation module not initialized')

    if context['stopFlag']:
        raise error.NoDataNotification()

    sqlOid = '.'.join(['%10s' % x for x in oid.split('.')])
    if 'hexvalue' in context:
        textTag = context['hextag']
        textValue = context['hexvalue']
    else:
        textTag = SnmprecGrammar().getTagByType(context['origValue'])
        textValue = str(context['origValue'])
 
    cursor = dbConn.cursor()

    cursor.execute(
        'select oid from %s where oid=? limit 1' % dbTable, (sqlOid,)
    )
    if cursor.fetchone():
        cursor.execute(
            'update %s set tag=?,value=? where oid=?' % dbTable, (textTag, textValue, sqlOid)
        )
    else:
        cursor.execute(
            'insert into %s values (?, ?, ?, "read-write")' % dbTable, (sqlOid, textTag, textValue)
        )
    cursor.close()

    if not context['count']:
        return str(context['startOID']), ':sql', dbTable
    else:
        raise error.NoDataNotification()

def shutdown(snmpEngine, **context):
    if dbConn is not None:
        dbConn.commit()
        dbConn.close()
