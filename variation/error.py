# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate SNMP error response

import sys
from snmpsim.grammar.snmprec import SnmprecGrammar
from pysnmp.smi import error

errorTypes = {
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

settingsCache = {}

def init(snmpEngine, **context): pass

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if oid not in settingsCache:
        settingsCache[oid] = dict([x.split('=') for x in value.split(',')])

        if 'hexvalue' in settingsCache[oid]:
            settingsCache[oid]['value'] = [int(settingsCache[oid]['hexvalue'][x:x+2], 16) for x in range(0, len(settingsCache[oid]['hexvalue']), 2)]

        if 'status' in settingsCache[oid]:
            settingsCache[oid]['status'] = settingsCache[oid]['status'].lower()

        if 'op' not in settingsCache[oid]:
            settingsCache[oid]['op'] = 'any'

        if 'vlist' in settingsCache[oid]:
            vlist = {}
            settingsCache[oid]['vlist'] = settingsCache[oid]['vlist'].split(':')
            while settingsCache[oid]['vlist']:
                o,v,e = settingsCache[oid]['vlist'][:3]
                settingsCache[oid]['vlist'] = settingsCache[oid]['vlist'][3:]
                v = SnmprecGrammar.tagMap[tag](v)
                if o not in vlist:
                    vlist[o] = {}
                if o == 'eq':
                    vlist[o][v] = e
                elif o in ('lt', 'gt'):
                    vlist[o] = v, e
                else:
                    sys.stdout.write('delay: bad vlist syntax: %s\r\n' % settingsCache[oid]['vlist'])
            settingsCache[oid]['vlist'] = vlist

    e = None

    if context['setFlag']:
        if 'vlist' in settingsCache[oid]:
            if 'eq' in settingsCache[oid]['vlist'] and  \
                  context['origValue'] in settingsCache[oid]['vlist']['eq']:
                e = settingsCache[oid]['vlist']['eq'][context['origValue']]
            elif 'lt' in settingsCache[oid]['vlist'] and  \
                  context['origValue'] < settingsCache[oid]['vlist']['lt'][0]:
                e = settingsCache[oid]['vlist']['lt'][1]
            elif 'gt' in settingsCache[oid]['vlist'] and  \
                  context['origValue'] > settingsCache[oid]['vlist']['gt'][0]:
                e = settingsCache[oid]['vlist']['gt'][1]
        elif settingsCache[oid]['op'] in ('set', 'any'):
            if 'status' in settingsCache[oid]:
                e = settingsCache[oid]['status']
    else:        
        if settingsCache[oid]['op'] in ('get', 'any'):
            if 'status' in settingsCache[oid]:
                e = settingsCache[oid]['status']

    if e and e in errorTypes:
        raise errorTypes[e](
            name=oid, idx=context['varsTotal']-context['varsRemaining']
        )

    if context['setFlag']:
        settingsCache[oid]['value'] = context['origValue']

    return oid, tag, settingsCache[oid].get('value', context['errorStatus'])

def shutdown(snmpEngine, **context): pass 
