#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a writable Agent using
# SQL backend for storing Managed Objects
#
# Module initialization parameters are dbtype:<dbms>,dboptions:<options>
#
# Expects to work a table of the following layout:
# CREATE TABLE <tablename> (oid text, tag text, value text, maxaccess text)
#
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.mltsplit import split
from snmpsim import error, log

isolationLevels = {
    '0': 'READ UNCOMMITTED',
    '1': 'READ COMMITTED',
    '2': 'REPEATABLE READ',
    '3': 'SERIALIZABLE'
}

def init(**context):
    options = {}
    if context['options']:
        options.update(
            dict([split(x, ':') for x in split(context['options'], ',')])
        )
    if 'dbtype' not in options:
        raise error.SnmpsimError('database type not specified')
    db = __import__(
        options['dbtype'], 
        globals(), locals(),
        options['dbtype'].split('.')[:-1]
    )
    if 'dboptions' in options: # legacy
        connectParams = { 'database': options['dboptions'] }
    else:
        connectParams = dict(
            [ (k,options[k]) for k in options if k in ('host', 'port', 'user', 'passwd', 'password', 'db', 'database', 'unix_socket', 'named_pipe') ]
        )
        for k in 'port', 'connect_timeout':
            if k in connectParams:
                connectParams[k] = int(connectParams[k])
    if not connectParams:
        raise error.SnmpsimError('database connect parameters not specified')
    moduleContext['dbConn'] = dbConn = db.connect(**connectParams)
    moduleContext['dbTable'] = dbTable = options.get('dbtable', 'snmprec')
    moduleContext['isolationLevel'] = options.get('isolationlevel', '1')
    if moduleContext['isolationLevel'] not in isolationLevels:
        raise error.SnmpsimError('unknown SQL transaction isolation level %s' % moduleContext['isolationLevel'])

    if 'mode' in context and context['mode'] == 'recording':
        cursor = dbConn.cursor()

        try:
            cursor.execute(
                'select * from information_schema.tables where table_name=\'%s\' limit 1' % dbTable
            )
        except: # non-ANSI database
            try:
                cursor.execute('select * from %s limit 1' % dbTable)
            except:
                createTable = True
            else:
                createTable = False
        else:
            createTable = not cursor.fetchone()

        if createTable:
            cursor.execute('CREATE TABLE %s (oid text, tag text, value text, maxaccess text)' % dbTable)

        cursor.close()

def variate(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    cursor = dbConn.cursor()

    try:
        cursor.execute(
            'set session transaction isolation level %s' % moduleContext['isolationLevel']
        )
        cursor.fetchall()
    except:  # non-MySQL/Postgres
        pass

    if value:
        dbTable = value.split(',').pop(0)
    elif 'dbTable' in moduleContext:
        dbTable = moduleContext['dbTable']
    else:
        log.msg('SQL table not specified for OID %s' % (context['origOid'],))
        return context['origOid'], tag, context['errorStatus']

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
            'select maxaccess,tag from %s where oid=\'%s\' limit 1' % (dbTable, sqlOid)
        )
        resultset = cursor.fetchone()
        if resultset:
            maxaccess = resultset[0]
            if maxaccess != 'read-write':
                return origOid, tag, context['errorStatus']
            cursor.execute(
                'update %s set tag=\'%s\',value=\'%s\' where oid=\'%s\'' % (dbTable, textTag, textValue, sqlOid)
            )
        else:
            cursor.execute(
                'insert into %s values (\'%s\', \'%s\', \'%s\', \'read-write\')' % (dbTable, sqlOid, textTag, textValue)
            )
        if context['varsRemaining'] == 0:  # last OID in PDU
            dbConn.commit()
        cursor.close()
        return origOid, textTag, context['origValue']
    else:
        if context['nextFlag']:
            cursor.execute('select oid from %s where oid>\'%s\' order by oid limit 1' % (dbTable, sqlOid))
            resultset = cursor.fetchone()
            if resultset:
                origOid = origOid.clone(
                  '.'.join([x.strip() for x in str(resultset[0]).split('.')])
                )
                sqlOid = '.'.join(['%10s' % x for x in str(origOid).split('.')])
            else:
                cursor.close()
                return origOid, tag, context['errorStatus']

        cursor.execute('select tag, value from %s where oid=\'%s\' limit 1' % (dbTable, sqlOid))
        resultset = cursor.fetchone()
        cursor.close()

        if resultset:
            return origOid, str(resultset[0]), str(resultset[1])
        else:
            return origOid, tag, context['errorStatus']

def record(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        dbConn = moduleContext['dbConn']
    else:
        raise error.SnmpsimError('variation module not initialized')

    dbTable = moduleContext['dbTable']

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
        'select oid from %s where oid=\'%s\' limit 1' % (dbTable, sqlOid)
    )
    if cursor.fetchone():
        cursor.execute(
            'update %s set tag=\'%s\',value=\'%s\' where oid=\'%s\'' % (dbTable, textTag, textValue, sqlOid)
        )
    else:
        cursor.execute(
            'insert into %s values (\'%s\', \'%s\', \'%s\', \'read-write\')' % (dbTable, sqlOid, textTag, textValue)
        )
    cursor.close()

    if not context['count']:
        return str(context['startOID']), ':sql', dbTable
    else:
        raise error.NoDataNotification()

def shutdown(**context):
    dbConn = moduleContext.get('dbConn')
    if dbConn:
        if 'mode' in context and context['mode'] == 'recording':
            dbConn.commit()
        dbConn.close()
