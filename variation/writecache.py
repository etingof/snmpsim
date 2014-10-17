# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variaton module
# Simulate a writable Agent
import shelve
from pysnmp.smi import error
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.mltsplit import split
from snmpsim import log

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

def init(**context):
    moduleContext['settings'] = {}
    if context['options']:
        moduleContext['settings'].update(
            dict([split(x, ':') for x in split(context['options'], ',')])
        )
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
                    log.msg('writecache: bad vlist syntax: %s' % recordContext['settings']['vlist'])
            recordContext['settings']['vlist'] = vlist

    if oid not in moduleContext:
        moduleContext[oid] = {}
        moduleContext[oid]['type'] = SnmprecGrammar().tagMap[tag]()

    textOid = str(oid)

    if context['setFlag']:
        if 'vlist' in recordContext['settings']:
            if 'eq' in recordContext['settings']['vlist'] and  \
                     context['origValue'] in recordContext['settings']['vlist']['eq']:
                e = recordContext['settings']['vlist']['eq'][context['origValue']]
            elif 'lt' in recordContext['settings']['vlist'] and  \
                     context['origValue']<recordContext['settings']['vlist']['lt'][0]:
                e = recordContext['settings']['vlist']['lt'][1]
            elif 'gt' in recordContext['settings']['vlist'] and  \
                     context['origValue']>recordContext['settings']['vlist']['gt'][0]:
                e = recordContext['settings']['vlist']['gt'][1]
            else:
                e = None

            if e in errorTypes:
                raise errorTypes[e](
                    name=oid, idx=max(0, context['varsTotal']-context['varsRemaining']-1)
                )

        if moduleContext[oid]['type'].isSameTypeWith(context['origValue']):
            moduleContext['cache'][textOid] = context['origValue']
        else:
            return context['origOid'], tag, context['errorStatus']

    if textOid in moduleContext['cache']:
        return oid, tag, moduleContext['cache'][textOid]
    elif 'hexvalue' in recordContext['settings']:
        return oid, tag, moduleContext[oid]['type'].clone(hexValue=recordContext['settings']['hexvalue'])
    elif 'value' in recordContext['settings']:
        return oid, tag, moduleContext[oid]['type'].clone(recordContext['settings']['value'])
    else:
        return oid, tag, context['errorStatus']

def shutdown(**context):
    if 'file' in moduleContext['settings']:
        moduleContext['cache'].close()
