# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate request processing delay
import sys
import time
import random

settingsCache = {}

def init(snmpEngine, *args):
    random.seed()

def process(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], context['errorStatus']  # serve exact OIDs
    if context['setFlag']:
        return context['origOid'], context['errorStatus']  # read-only mode

    if oid not in settingsCache:
        if '=' not in value:
            settingsCache[oid] = { 'value': value }
        else:
            settingsCache[oid] = dict([x.split('=') for x in value.split(',')])

    if 'hexvalue' in settingsCache[oid]:
        settingsCache[oid]['value'] = [int(settingsCache[oid]['hexvalue'][x:x+2], 16) for x in range(0, len(settingsCache[oid]['hexvalue']), 2)]

    if 'value' not in settingsCache[oid]:
        sys.stdout.write('delay: missing value part for oid %s\r\n' % (oid,))
        return oid, context['errorStatus']

    delay = float(settingsCache[oid].get('wait', 500))

    d = float(settingsCache[oid].get('deviation', 0))
    if d:
        delay += random.randrange(-d, d)

    if delay < 0:
        delay = 0

    time.sleep(delay/1000)

    return oid, settingsCache[oid]['value']

def shutdown(snmpEngine, *args): pass 
