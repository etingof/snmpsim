#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# Managed value variation module: simulate a writable Agent using
# SQL backend for storing Managed Objects
#
# Module initialization parameters are dbtype:<dbms>,dboptions:<options>
#
# Expects to work a table of the following layout:
# CREATE TABLE <tablename> (oid text, tag text, value text, maxaccess text)
#
from snmpsim import error
from snmpsim import log
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.utils import split

ISOLATION_LEVELS = {
    '0': 'READ UNCOMMITTED',
    '1': 'READ COMMITTED',
    '2': 'REPEATABLE READ',
    '3': 'SERIALIZABLE'
}


def init(**context):
    options = {}

    if context['options']:
        options.update(
            dict([split(x, ':')
                  for x in split(context['options'], ',')]))

    if 'dbtype' not in options:
        raise error.SnmpsimError('database type not specified')

    db = __import__(
        options['dbtype'],
        globals(), locals(),
        options['dbtype'].split('.')[:-1]
    )

    if 'dboptions' in options:  # legacy
        connectParams = {
            'database': options['dboptions']
        }

    else:
        connectOpts = ('host', 'port', 'user', 'passwd', 'password',
                       'db', 'database', 'unix_socket', 'named_pipe')

        connectParams = dict(
            [(k, options[k]) for k in options if k in connectOpts])

        for k in 'port', 'connect_timeout':
            if k in connectParams:
                connectParams[k] = int(connectParams[k])

    if not connectParams:
        raise error.SnmpsimError('database connect parameters not specified')

    moduleContext['dbConn'] = dbConn = db.connect(**connectParams)
    moduleContext['dbTable'] = dbTable = options.get('dbtable', 'snmprec')
    moduleContext['isolationLevel'] = options.get('isolationlevel', '1')

    if moduleContext['isolationLevel'] not in ISOLATION_LEVELS:
        raise error.SnmpsimError(
            'unknown SQL transaction isolation level '
            '%s' % moduleContext['isolationLevel'])

    if 'mode' in context and context['mode'] == 'recording':
        cursor = dbConn.cursor()

        try:
            cursor.execute(
                'select * from information_schema.tables '
                'where table_name=\'%s\' limit 1' % dbTable)

        except Exception:  # non-ANSI database

            try:
                cursor.execute('select * from %s limit 1' % dbTable)

            except Exception:
                createTable = True

            else:
                createTable = False

        else:
            createTable = not cursor.fetchone()

        if createTable:
            cursor.execute(
                'CREATE TABLE %s (oid text, tag text, value text, '
                'maxaccess text)' % dbTable)

        cursor.close()


def variate(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        db_conn = moduleContext['dbConn']

    else:
        raise error.SnmpsimError('variation module not initialized')

    cursor = db_conn.cursor()

    try:
        cursor.execute(
            'set session transaction isolation level '
            '%s' % ISOLATION_LEVELS[moduleContext['isolationLevel']])
        cursor.fetchall()

    except Exception:  # non-MySQL/Postgres
        pass

    if value:
        db_table = value.split(',').pop(0)

    elif 'dbTable' in moduleContext:
        db_table = moduleContext['dbTable']

    else:
        log.info('SQL table not specified for OID '
                '%s' % (context['origOid'],))
        return context['origOid'], tag, context['errorStatus']

    orig_oid = context['origOid']
    sql_oid = '.'.join(['%10s' % x for x in str(orig_oid).split('.')])

    if context['setFlag']:
        if 'hexvalue' in context:
            text_tag = context['hextag']
            text_value = context['hexvalue']

        else:
            text_tag = SnmprecGrammar().get_tag_by_type(context['origValue'])
            text_value = str(context['origValue'])

        cursor.execute(
            'select maxaccess,tag from %s where oid=\'%s\''
            ' limit 1' % (db_table, sql_oid)
        )

        resultset = cursor.fetchone()

        if resultset:
            maxaccess = resultset[0]
            if maxaccess != 'read-write':
                return orig_oid, tag, context['errorStatus']

            cursor.execute(
                'update %s set tag=\'%s\',value=\'%s\' where '
                'oid=\'%s\'' % (db_table, text_tag, text_value, sql_oid))

        else:
            cursor.execute(
                'insert into %s values (\'%s\', \'%s\', \'%s\', '
                '\'read-write\')' % (db_table, sql_oid, text_tag, text_value))

        if context['varsRemaining'] == 0:  # last OID in PDU
            db_conn.commit()

        cursor.close()

        return orig_oid, text_tag, context['origValue']

    else:
        if context['nextFlag']:
            cursor.execute(
                'select oid from %s where oid>\'%s\' order by oid '
                'limit 1' % (db_table, sql_oid))

            resultset = cursor.fetchone()

            if resultset:
                orig_oid = orig_oid.clone(
                    '.'.join([x.strip() for x in str(resultset[0]).split('.')]))

                sql_oid = '.'.join(['%10s' % x for x in str(orig_oid).split('.')])

            else:
                cursor.close()
                return orig_oid, tag, context['errorStatus']

        cursor.execute(
            'select tag, value from %s where oid=\'%s\' '
            'limit 1' % (db_table, sql_oid))

        resultset = cursor.fetchone()

        cursor.close()

        if resultset:
            return orig_oid, str(resultset[0]), str(resultset[1])

        else:
            return orig_oid, tag, context['errorStatus']


def record(oid, tag, value, **context):
    if 'dbConn' in moduleContext:
        db_conn = moduleContext['dbConn']

    else:
        raise error.SnmpsimError('variation module not initialized')

    db_table = moduleContext['dbTable']

    if context['stopFlag']:
        raise error.NoDataNotification()

    sql_oid = '.'.join(['%10s' % x for x in oid.split('.')])
    if 'hexvalue' in context:
        text_tag = context['hextag']
        text_value = context['hexvalue']

    else:
        text_tag = SnmprecGrammar().get_tag_by_type(context['origValue'])
        text_value = str(context['origValue'])

    cursor = db_conn.cursor()

    cursor.execute(
        'select oid from %s where oid=\'%s\' '
        'limit 1' % (db_table, sql_oid))

    if cursor.fetchone():
        cursor.execute(
            'update %s set tag=\'%s\',value=\'%s\' where '
            'oid=\'%s\'' % (db_table, text_tag, text_value, sql_oid))

    else:
        cursor.execute(
            'insert into %s values (\'%s\', \'%s\', \'%s\', '
            '\'read-write\')' % (db_table, sql_oid, text_tag, text_value))

    cursor.close()

    if not context['count']:
        return str(context['startOID']), ':sql', db_table

    else:
        raise error.NoDataNotification()


def shutdown(**context):
    db_conn = moduleContext.get('dbConn')
    if db_conn:
        if 'mode' in context and context['mode'] == 'recording':
            db_conn.commit()

        db_conn.close()
