#
# SNMP Simulator, http://snmpsim.sourceforge.net
#
# Managed value variation module: simulate a writable Agent using
# SQL backend
#
# Module initialization parameters hold dbms-type,database-name
# parameters, while data file value should refer to a database table name
#
# Expects to work a table of the following layout:
# CREATE TABLE <tablename> (oid text primary key, tag text, value text,
#                           maxaccess text default "read-only")
#
from snmpsim.grammar.snmprec import SnmprecGrammar

dbConn = None

def init(snmpEngine, *args):
    global dbConn
    if len(args) < 2:
        raise Exception('database type and name not specified')
    db = __import__(args[0])
    dbConn = db.connect(args[1])

def process(oid, tag, value, **context):
    if dbConn is None:
        raise Exception('variation module not initialized')

    cursor = dbConn.cursor()

    dbTable, = value.split(',')

    origOid = context['origOid']

    if context['setFlag']:
        cursor.execute('select maxaccess,tag from %s where oid=?' % dbTable, (str(origOid),))
        resultset = cursor.fetchone()
        if resultset:
            maxaccess = resultset[0]
            if maxaccess != 'read-write':
                return origOid, context['errorStatus']
            origTag = resultset[1]
            cursor.execute('update %s set value=? where oid=?' % dbTable, (str(SnmprecGrammar.tagMap[origTag](value)), str(origOid)))
        else:
            origTag = str(sum([ x for x in context['origValue'].tagSet[0]]))
            cursor.execute('insert into %s values (?, ?, ?, "read-write")' % dbTable, (str(origOid), origTag, str(context['origValue'])))
        if context['varsRemaining'] == 0:
            dbConn.commit()
        return origOid, context['origValue']
    else:
        if context['nextFlag']:
            cursor.execute('select oid from %s where oid>? order by oid limit 1' % dbTable, (str(origOid),))
            resultset = cursor.fetchone()
            if resultset:
                origOid = origOid.clone(str(resultset[0]))
            else:
                return origOid, context['errorStatus']

        cursor.execute('select tag, value from %s where oid=?' % dbTable, (str(origOid),))
        resultset = cursor.fetchone()
        if resultset:
            return origOid, SnmprecGrammar.tagMap[resultset[0]](str(resultset[1]))
        else:
            return origOid, context['errorStatus']

def shutdown(snmpEngine, *args):
    if dbConn is not None:
        dbConn.close()
