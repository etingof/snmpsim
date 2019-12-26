#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Simulator, http://snmplabs.com/snmpsim
#
# Managed value variation module: simulate a writable Agent
#
import shelve

from pysnmp.smi import error

from snmpsim import log
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.record.snmprec import SnmprecRecord
from snmpsim.utils import split

ERROR_TYPES = {
    'generror': error.GenError,
    'noaccess': error.NoAccessError,
    'wrongtype': error.WrongTypeError,
    'wrongvalue': error.WrongValueError,
    'nocreation': error.NoCreationError,
    'inconsistentvalue': error.InconsistentValueError,
    'resourceunavailable': error.ResourceUnavailableError,
    'commitfailed': error.CommitFailedError,
    'undofailed': error.UndoFailedError,
    'authorizationerror': error.AuthorizationError,
    'notwritable': error.NotWritableError,
    'inconsistentname': error.InconsistentNameError,
    'nosuchobject': error.NoSuchObjectError,
    'nosuchinstance': error.NoSuchInstanceError,
    'endofmib': error.EndOfMibViewError
}


def init(**context):
    moduleContext['settings'] = {}

    if context['options']:
        moduleContext['settings'].update(
            dict([split(x, ':')
                  for x in split(context['options'], ',')]))

    if 'file' in moduleContext['settings']:
        moduleContext['cache'] = shelve.open(moduleContext['settings']['file'])

    else:
        moduleContext['cache'] = {}


def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if 'settings' not in recordContext:
        recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])

        if 'vlist' in recordContext['settings']:

            vlist = {}

            recordContext['settings']['vlist'] = split(
                recordContext['settings']['vlist'], ':')

            while recordContext['settings']['vlist']:
                o, v, e = recordContext['settings']['vlist'][:3]

                vl = recordContext['settings']['vlist'][3:]
                recordContext['settings']['vlist'] = vl

                type_tag, _ = SnmprecRecord.unpack_tag(tag)

                v = SnmprecGrammar.TAG_MAP[type_tag](v)

                if o not in vlist:
                    vlist[o] = {}

                if o == 'eq':
                    vlist[o][v] = e

                elif o in ('lt', 'gt'):
                    vlist[o] = v, e

                else:
                    log.info('writecache: bad vlist syntax: '
                            '%s' % recordContext['settings']['vlist'])

            recordContext['settings']['vlist'] = vlist

        if 'status' in recordContext['settings']:
            st = recordContext['settings']['status'].lower()
            recordContext['settings']['status'] = st

    if oid not in moduleContext:
        moduleContext[oid] = {}

        type_tag, _ = SnmprecRecord.unpack_tag(tag)

        moduleContext[oid]['type'] = SnmprecGrammar.TAG_MAP[type_tag]()

    text_oid = str(oid)

    if context['setFlag']:
        if 'vlist' in recordContext['settings']:
            if ('eq' in recordContext['settings']['vlist'] and
                    context['origValue'] in recordContext['settings']['vlist']['eq']):
                e = recordContext['settings']['vlist']['eq'][context['origValue']]

            elif ('lt' in recordContext['settings']['vlist'] and
                    context['origValue'] < recordContext['settings']['vlist']['lt'][0]):
                e = recordContext['settings']['vlist']['lt'][1]

            elif ('gt' in recordContext['settings']['vlist'] and
                    context['origValue'] > recordContext['settings']['vlist']['gt'][0]):
                e = recordContext['settings']['vlist']['gt'][1]

            else:
                e = None

            if e in ERROR_TYPES:
                idx = max(0, context['varsTotal'] - context['varsRemaining'] - 1)
                raise ERROR_TYPES[e](name=oid, idx=idx)

        if moduleContext[oid]['type'].isSameTypeWith(context['origValue']):
            moduleContext['cache'][text_oid] = context['origValue']

        else:
            return context['origOid'], tag, context['errorStatus']

    if 'status' in recordContext['settings']:

        if ('op' not in recordContext['settings'] or
                recordContext['settings']['op'] == 'any' or
                recordContext['settings']['op'] == 'set' and context['setFlag'] or
                recordContext['settings']['op'] == 'get' and not context['setFlag']):

            e = recordContext['settings']['status']

            if e in ERROR_TYPES:
                idx = max(0, context['varsTotal'] - context['varsRemaining'] - 1)
                raise ERROR_TYPES[e](name=oid, idx=idx)

    if text_oid in moduleContext['cache']:
        return oid, tag, moduleContext['cache'][text_oid]

    elif 'hexvalue' in recordContext['settings']:
        return oid, tag, moduleContext[oid]['type'].clone(
            hexValue=recordContext['settings']['hexvalue'])

    elif 'value' in recordContext['settings']:
        return oid, tag, moduleContext[oid]['type'].clone(
            recordContext['settings']['value'])

    else:
        return oid, tag, context['errorStatus']


def shutdown(**context):
    if 'file' in moduleContext['settings']:
        moduleContext['cache'].close()
