# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate a numeric value
# Valid values in taglist are:
#   Integer     - 2
#   Counter32   - 65
#   Gauge32     - 66
#   TimeTicks   - 67
#   Counter64   - 70
import math
import time
import random
from pysnmp.proto import rfc1902

settingsCache = {}
valuesCache = {}

booted = time.time()

def init(snmpEngine, *args):
    random.seed()

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], context['errorStatus']  # serve exact OIDs
    if context['setFlag']:
        return context['origOid'], context['errorStatus']  # read-only mode

    if oid not in settingsCache:
        settingsCache[oid] = dict([ x.split('=') for x in value.split(',') ])
        if 'min' not in settingsCache[oid]:
            settingsCache[oid]['min'] = 0
        if 'max' not in settingsCache[oid]:
            if tag == '67':
                settingsCache[oid]['max'] = 0xffffffffffffffff
            else:
                settingsCache[oid]['max'] = 0xffffffff

    if oid not in valuesCache:
        valuesCache[oid] = float(settingsCache[oid].get('initial', settingsCache[oid]['min'])), booted

    v, t = valuesCache[oid]

    if 'function' in settingsCache[oid]:
        f = getattr(math, settingsCache[oid]['function'])
    else:
        f = lambda x: x

    v += f((time.time() - t) * float(settingsCache[oid].get('rate', 1)))
    
    if 'increasing' in settingsCache[oid]:
        v = abs(v)
     
    v *= float(settingsCache[oid].get('scale', 1)) + float(settingsCache[oid].get('offset', 0))

    d = int(settingsCache[oid].get('deviation', 0))
    if d:
        if 'increasing' in settingsCache[oid]:
            v += random.randrange(0, d)
        else:
            v += random.randrange(-d, d)

    if v < settingsCache[oid]['min']:
        v = settingsCache[oid]['min']
    elif v > settingsCache[oid]['max']:
        if 'wrap' in settingsCache[oid]:
            v = settingsCache[oid]['min']
        else:
            v = settingsCache[oid]['max']

    if 'increasing' in settingsCache[oid]:
        valuesCache[oid] = v, time.time()

    return oid, v

def record(oid, tag, value, **context):
    if 'options' in context:
        options = dict([ x.split('=') for x in context['options'].split(',') ])
        if 'taglist' in options and tag in options['taglist']:
            del options['taglist']
            if context['origValue'].tagSet in (rfc1902.Counter32.tagSet,
                                               rfc1902.Counter64.tagSet,
                                               rfc1902.TimeTicks.tagSet,
                                               rfc1902.Gauge32.tagSet,
                                               rfc1902.Integer.tagSet):
                tag += ':numeric'
                value = 'initial=' + value
                if options:
                    value += ',' + \
                        ','.join(['%s=%s' % (k,v) for k,v in options.items()])
                if context['origValue'].tagSet not in (rfc1902.Gauge32.tagSet,
                                                       rfc1902.Integer.tagSet):
                    if 'increasing' not in context:
                        value += ',increasing=1' 
                if context['origValue'].tagSet == rfc1902.TimeTicks.tagSet:
                    if 'rate' not in context:
                        value += ',rate=100'
                if context['origValue'].tagSet == rfc1902.Integer.tagSet:
                    if 'rate' not in context:
                        value += ',rate=0'
                return oid, tag, value

    return oid, 'hextag' in context and context['hextag'] or tag, value

def shutdown(snmpEngine, *args): pass 
