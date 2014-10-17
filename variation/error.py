# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate SNMP error response

import sys
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim import log
from snmpsim.mltsplit import split
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

def init(**context): pass

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if 'settings' not in recordContext:
        recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])

        if 'hexvalue' in recordContext['settings']:
            recordContext['settings']['value'] = [int(recordContext['settings']['hexvalue'][x:x+2], 16) for x in range(0, len(recordContext['settings']['hexvalue']), 2)]

        if 'status' in recordContext['settings']:
            recordContext['settings']['status'] = recordContext['settings']['status'].lower()

        if 'op' not in recordContext['settings']:
            recordContext['settings']['op'] = 'any'

        if 'vlist' in recordContext['settings']:
            vlist = {}
            recordContext['settings']['vlist'] = split(recordContext['settings']['vlist'], ':')
            while recordContext['settings']['vlist']:
                o,v,e = recordContext['settings']['vlist'][:3]
                recordContext['settings']['vlist'] = recordContext['settings']['vlist'][3:]
                v = SnmprecGrammar.tagMap[tag](v)
                if o not in vlist:
                    vlist[o] = {}
                if o == 'eq':
                    vlist[o][v] = e
                elif o in ('lt', 'gt'):
                    vlist[o] = v, e
                else:
                    log.msg('error: bad vlist syntax: %s' % recordContext['settings']['vlist'])
            recordContext['settings']['vlist'] = vlist

    e = None

    if context['setFlag']:
        if 'vlist' in recordContext['settings']:
            if 'eq' in recordContext['settings']['vlist'] and  \
                  context['origValue'] in recordContext['settings']['vlist']['eq']:
                e = recordContext['settings']['vlist']['eq'][context['origValue']]
            elif 'lt' in recordContext['settings']['vlist'] and  \
                  context['origValue'] < recordContext['settings']['vlist']['lt'][0]:
                e = recordContext['settings']['vlist']['lt'][1]
            elif 'gt' in recordContext['settings']['vlist'] and  \
                  context['origValue'] > recordContext['settings']['vlist']['gt'][0]:
                e = recordContext['settings']['vlist']['gt'][1]
        elif recordContext['settings']['op'] in ('set', 'any'):
            if 'status' in recordContext['settings']:
                e = recordContext['settings']['status']
    else:        
        if recordContext['settings']['op'] in ('get', 'any'):
            if 'status' in recordContext['settings']:
                e = recordContext['settings']['status']

    if e and e in errorTypes:
        log.msg('error: reporting %s for %s' % (e, oid))
        raise errorTypes[e](
            name=oid, idx=max(0, context['varsTotal']-context['varsRemaining']-1)
        )

    if context['setFlag']:
        recordContext['settings']['value'] = context['origValue']

    return oid, tag, recordContext['settings'].get('value', context['errorStatus'])

def shutdown(**context): pass 
