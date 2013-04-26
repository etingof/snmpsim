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
from pysnmp.proto import rfc1902, rfc1905
from snmpsim import log
from snmpsim import error

settingsCache = {}
valuesCache = {}
moduleOptions = {}
moduleContext = {}

tboot = time.time()

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
        for k in settingsCache[oid]:
            if k != 'function' and k in settingsCache[oid]:
                settingsCache[oid][k] = float(settingsCache[oid][k])
        if 'min' not in settingsCache[oid]:
            settingsCache[oid]['min'] = 0
        if 'max' not in settingsCache[oid]:
            if tag == '70':
                settingsCache[oid]['max'] = 0xffffffffffffffff
            else:
                settingsCache[oid]['max'] = 0xffffffff
        if settingsCache[oid]['min'] > settingsCache[oid]['max']:
            settingsCache[oid]['max'] = settingsCache[oid]['min'] + 1
        if 'rate' not in settingsCache[oid]:
            settingsCache[oid]['rate'] = 1
        if 'function' in settingsCache[oid]:
            settingsCache[oid]['function'] = getattr(math, settingsCache[oid]['function'])
        else:
            settingsCache[oid]['function'] = lambda x: x

    if oid not in valuesCache:
        valuesCache[oid] = settingsCache[oid].get('initial', settingsCache[oid]['min']), tboot

    vold, told = valuesCache[oid]

    tnow = time.time()

    if 'atime' in settingsCache[oid]:
        t = tnow
    else:
        t = tnow - tboot

    v = settingsCache[oid]['function'](
        t * settingsCache[oid]['rate']
    )
    
    if 'scale' in settingsCache[oid]:
        v *= settingsCache[oid]['scale']

    if 'offset' in settingsCache[oid]:
        if 'cumulative' in settingsCache[oid]:
            v += settingsCache[oid]['offset'] * (tnow - told)
        else:
            v += settingsCache[oid]['offset']

    if 'deviation' in settingsCache[oid]:
        v += random.randrange(-settingsCache[oid]['deviation'], settingsCache[oid]['deviation'])

    if 'cumulative' in settingsCache[oid]:
        v += vold

    if 'increasing' in settingsCache[oid]:
        v = max(v, vold)

    if v < settingsCache[oid]['min']:
        v = settingsCache[oid]['min']
    elif v > settingsCache[oid]['max']:
        if 'wrap' in settingsCache[oid]:
            v = settingsCache[oid]['min']
        else:
            v = settingsCache[oid]['max']

    if 'cumulative' in settingsCache[oid]:
        valuesCache[oid] = v, tnow

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
            settings = {
                'initial': value
            }
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
                log.msg('numeric: waiting %.2f sec(s), %s OIDs dumped, %s iterations remaining...\r\n' % (wait, context['total']+context['count'], moduleOptions['iterations']))
                time.sleep(wait)
                moduleOptions['iterations'] -= 1
                moduleContext['started'] = time.time()
                raise error.MoreDataNotification()
            else:
                if oid in moduleContext:
                    moduleContext[oid]['time'] = time.time()
                    moduleContext[oid]['value'] = context['origValue']
                raise error.NoDataNotification()
        else:
            if oid in moduleContext and 'value' in moduleContext[oid]:
                if not rfc1905.endOfMibView.isSameTypeWith(context['origValue']) and not rfc1905.endOfMibView.isSameTypeWith(moduleContext[oid]['value']):
                    moduleContext[oid]['rate'] = (int(context['origValue']) - int(moduleContext[oid]['value'])) / (time.time() - moduleContext[oid]['time'])

                del moduleContext[oid]['value'];
                del moduleContext[oid]['time'];

                value = ','.join(
                    [ '%s=%s' % (k,v) for k,v in moduleContext[oid].items() ]
                )

            return oid, tag, value
    else:
        return oid, tag, value

def shutdown(snmpEngine, **context): pass 
