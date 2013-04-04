# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variaton module
# Simulate a writable Agent
import shelve
from pysnmp.smi import error
from snmpsim.grammar.snmprec import SnmprecGrammar

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
moduleOptions = {}
moduleContext = {}

def init(snmpEngine, **context):
    if context['options']:
        moduleOptions.update(
            dict([x.split(':') for x in context['options'].split(',')])
        )
    if 'file' in moduleOptions:
        moduleContext['cache'] = shelve.open(moduleOptions['file'])
    else:
        moduleContext['cache'] = {}

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if oid not in settingsCache:
        settingsCache[oid] = dict([x.split('=') for x in value.split(',')])

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

    textOid = str(oid)

    if context['setFlag']:
        if 'vlist' in settingsCache[oid]:
            if 'eq' in settingsCache[oid]['vlist'] and  \
                     context['origValue'] in settingsCache[oid]['vlist']['eq']:
                e = settingsCache[oid]['vlist']['eq'][context['origValue']]
            elif 'lt' in settingsCache[oid]['vlist'] and  \
                     context['origValue']<settingsCache[oid]['vlist']['lt'][0]:
                e = settingsCache[oid]['vlist']['lt'][1]
            elif 'gt' in settingsCache[oid]['vlist'] and  \
                     context['origValue']>settingsCache[oid]['vlist']['gt'][0]:
                e = settingsCache[oid]['vlist']['gt'][1]
            else:
                e = None

            if e in errorTypes:
                raise errorTypes[e](
                    name=oid, idx=context['varsTotal']-context['varsRemaining']
                )

        moduleContext['cache'][textOid] = context['origValue']
        moduleContext['cache']['1'] = 1

    if textOid in moduleContext['cache']:
        return oid, tag, moduleContext['cache'][textOid]
    elif 'hexvalue' in settingsCache[oid]:
        return oid, tag, SnmprecGrammar().tagMap[tag](hexValue=settingsCache[oid]['hexvalue'])
    elif 'value' in settingsCache[oid]:
        return oid, tag, SnmprecGrammar().tagMap[tag](settingsCache[oid]['value'])
    else:
        return oid, tag, context['errorStatus']

def shutdown(snmpEngine, **context):
    if 'file' in moduleOptions:
        moduleContext['cache'].close()
