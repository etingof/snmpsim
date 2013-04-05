# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate a numeric value
# Valid values in module options are:
#   2  - Integer
#   65 - Counter32
#   66 - Gauge32
#   67 - TimeTicks
#   70 - Counter64
import sys
import math
import time
import random
from pysnmp.proto import rfc1902
from snmpsim import error

settingsCache = {}
valuesCache = {}
moduleOptions = {}
moduleContext = {}

booted = time.time()

def init(snmpEngine, **context):
    if context['options']:
        for k,v in [x.split(':') for x in context['options'].split(',')]:
            if k == 'addon':
                if k in moduleOptions:
                    moduleOptions[k].append(v)
                else:
                    moduleOptions[k] = [v]
            else:
                moduleOptions[k] = v
    if context['mode'] == 'recording':
        if 'iterations' in moduleOptions:
            moduleOptions['iterations'] = int(moduleOptions['iterations'])
            if moduleOptions['iterations']:
                moduleOptions['iterations'] = 1  # no reason for more
        if 'period' in moduleOptions:
            moduleOptions['period'] = float(moduleOptions['period'])
        else:
            moduleOptions['period'] = 10.0
    random.seed()

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']
    if context['setFlag']:
        return context['origOid'], tag, context['errorStatus']

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

    return oid, tag, v

def record(oid, tag, value, **context):
    if 'started' not in moduleContext:
        moduleContext['started'] = time.time()
    if 'taglist' in moduleOptions and tag in moduleOptions['taglist']:
        if context['origValue'].tagSet in (rfc1902.Counter32.tagSet,
                                           rfc1902.Counter64.tagSet,
                                           rfc1902.TimeTicks.tagSet,
                                           rfc1902.Gauge32.tagSet,
                                           rfc1902.Integer.tagSet):
            tag += ':numeric'
            settings = { 'initial': value }
            if context['origValue'].tagSet not in (rfc1902.Gauge32.tagSet,
                                                   rfc1902.Integer.tagSet):
                settings['increasing'] = 1
            if context['origValue'].tagSet == rfc1902.TimeTicks.tagSet:
                settings['rate'] = 100
            if context['origValue'].tagSet == rfc1902.Integer.tagSet:
                settings['rate'] = 0
            if 'addon' in moduleOptions:
                settings.update(
                    dict([x.split('=') for x in moduleOptions['addon']])
                )

            value = ','.join([ '%s=%s' % (k,v) for k,v in settings.items() ])

            if 'hextag' in context:
                del context['hextag']
            if 'hexvalue' in context:
                del context['hexvalue']

            if 'iterations' in moduleOptions and oid not in moduleContext:
                moduleContext[oid] = settings

    if 'hextag' in context and context['hextag']:
        tag = context['hextag']
    if 'hexvalue' in context and context['hexvalue']:
        value = context['hexvalue']

    if 'iterations' in moduleOptions:
        if moduleOptions['iterations']:
            if context['stopFlag']:
                wait = max(0, float(moduleOptions['period']) - (time.time() - moduleContext['started']))
                while wait > 0:
                    sys.stdout.write('numeric: waiting %.2f sec(s), %s OIDs dumped, %s iterations remaining...\r' % (wait, context['total']+context['count'], moduleOptions['iterations']))
                    sys.stdout.flush()
                    time.sleep(1)
                    wait -= 1
                sys.stdout.write(' ' * 77 + '\r')
                moduleOptions['iterations'] -= 1
                moduleContext['started'] = time.time()
                raise error.MoreDataNotification()
            else:
                if oid in moduleContext:
                    moduleContext[oid]['time'] = time.time()
                    moduleContext[oid]['value'] = context['origValue']
                raise error.NoDataNotification()
        else:
            if oid in moduleContext:
                moduleContext[oid]['rate'] = \
                    (context['origValue'] - moduleContext[oid]['value'])/\
                    (time.time() - moduleContext[oid]['time'])

                del moduleContext[oid]['value'];
                del moduleContext[oid]['time'];

                value = ','.join(
                    [ '%s=%s' % (k,v) for k,v in moduleContext[oid].items() ]
                )

            return oid, tag, value
    else:
        return oid, tag, value

def shutdown(snmpEngine, **context): pass 
