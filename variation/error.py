# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate SNMP error response

import sys
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

def init(snmpEngine, *args): pass

def process(oid, tag, value, **context):
    if oid not in settingsCache:
        settingsCache[oid] = dict([x.split('=') for x in value.split(',')])

    if 'hexvalue' in settingsCache[oid]:
        settingsCache[oid]['value'] = [int(settingsCache[oid]['hexvalue'][x:x+2], 16) for x in range(0, len(settingsCache[oid]['hexvalue']), 2)]

    if 'status' in settingsCache[oid]:
        settingsCache[oid]['status'] = settingsCache[oid]['status'].lower()

    if settingsCache[oid]['status'] not in errorTypes:
        sys.stdout.write('error: wrong/missing error status for oid %s\r\n' % (oid,))
        return oid, context['errorStatus']
 
    if 'op' not in settingsCache[oid]:
         settingsCache[oid]['op'] = 'any'

    if settingsCache[oid]['op'] not in ('get', 'set', 'any', '*'):
        sys.stdout.write('notification: unknown SNMP request type configured: %s\r\n' % settingsCache[oid]['op'])
        return context['origOid'], context['errorStatus']
 
    if settingsCache[oid]['op'] == 'get' and not context['setFlag'] or \
       settingsCache[oid]['op'] == 'set' and context['setFlag'] or \
       settingsCache[oid]['op'] in ('any', '*'):
        raise errorTypes[settingsCache[oid]['status']](
            name=oid, idx=context['varsTotal']-context['varsRemaining']
        )
    else:
        return oid, settingsCache[oid].get('value', context['errorStatus'])

def shutdown(snmpEngine, *args): pass 
