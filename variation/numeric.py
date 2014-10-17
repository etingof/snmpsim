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
from snmpsim.mltsplit import split
from snmpsim import log
from snmpsim import error

tboot = time.time()

def init(**context):
    if context['mode'] == 'variating':
        random.seed()
    if context['mode'] == 'recording':
        moduleContext['settings'] = {}
        if context['options']:
            for k,v in [split(x, ':') for x in split(context['options'], ',')]:
                if k == 'addon':
                    if k in moduleContext['settings']:
                        moduleContext['settings'][k].append(v)
                    else:
                        moduleContext['settings'][k] = [v]
                else:
                    moduleContext['settings'][k] = v
            if 'iterations' in moduleContext['settings']:
                moduleContext['settings']['iterations'] = int(moduleContext['settings']['iterations'])
                if moduleContext['settings']['iterations']:
                    moduleContext['settings']['iterations'] = 1  # no reason for more
            if 'period' in moduleContext['settings']:
                moduleContext['settings']['period'] = float(moduleContext['settings']['period'])
            else:
                moduleContext['settings']['period'] = 10.0

            if 'taglist' not in moduleContext['settings']:
                moduleContext['settings']['taglist'] = '2-65-66-67-70'

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']
    if context['setFlag']:
        return context['origOid'], tag, context['errorStatus']

    if 'settings' not in recordContext:
        recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])
        for k in recordContext['settings']:
            if k != 'function':
                recordContext['settings'][k] = float(recordContext['settings'][k])
        if 'min' not in recordContext['settings']:
            recordContext['settings']['min'] = 0
        if 'max' not in recordContext['settings']:
            if tag == '70':
                recordContext['settings']['max'] = 0xffffffffffffffff
            else:
                recordContext['settings']['max'] = 0xffffffff
        if 'rate' not in recordContext['settings']:
            recordContext['settings']['rate'] = 1
        if 'function' in recordContext['settings']:
            f = split(recordContext['settings']['function'], '%')
            recordContext['settings']['function'] = getattr(math, f[0]), f[1:]
        else:
            recordContext['settings']['function'] = lambda x: x, ()

    vold, told = recordContext['settings'].get('initial', recordContext['settings']['min']), tboot

    if 'cumulative' in recordContext['settings']:
        if 'value' not in recordContext:
            recordContext['value'] = vold, told
        vold, told = recordContext['value']

    tnow = time.time()

    if 'atime' in recordContext['settings']:
        t = tnow
    else:
        t = tnow - tboot

    f, args = recordContext['settings']['function']

    _args = []
    if args:
        for x in args:
            if x == '<time>':
                _args.append(t*recordContext['settings']['rate'])
            else:
                _args.append(float(x))
    else:
        _args.append(t*recordContext['settings']['rate'])

    v = f(*_args)
    
    if 'scale' in recordContext['settings']:
        v *= recordContext['settings']['scale']

    if 'offset' in recordContext['settings']:
        if 'cumulative' in recordContext['settings']:
            v += recordContext['settings']['offset'] * (tnow - told) * recordContext['settings']['rate']
        else:
            v += recordContext['settings']['offset']

    if 'deviation' in recordContext['settings'] and recordContext['settings']['deviation']:
        v += random.randrange(-recordContext['settings']['deviation'], recordContext['settings']['deviation'])

    if 'cumulative' in recordContext['settings']:
        v = max(v, 0)

    v += vold

    if v < recordContext['settings']['min']:
        v = recordContext['settings']['min']
    elif v > recordContext['settings']['max']:
        if 'wrap' in recordContext['settings']:
            v %= recordContext['settings']['max']
            v += recordContext['settings']['min']
        else:
            v = recordContext['settings']['max']

    if 'cumulative' in recordContext['settings']:
        recordContext['value'] = v, tnow

    return oid, tag, v

def record(oid, tag, value, **context):
    if 'started' not in moduleContext:
        moduleContext['started'] = time.time()

    if 'iterations' not in moduleContext:
        moduleContext['iterations'] = min(1, moduleContext['settings'].get('iterations',0))

    # single-run recording

    if 'iterations' not in moduleContext['settings'] or not moduleContext['settings']['iterations']:
        if context['origValue'].tagSet not in (
                    rfc1902.Counter32.tagSet,
                    rfc1902.Counter64.tagSet,
                    rfc1902.TimeTicks.tagSet,
                    rfc1902.Gauge32.tagSet,
                    rfc1902.Integer.tagSet):
            if 'hextag' in context:
                tag = context['hextag']
            if 'hexvalue' in context:
                value = context['hexvalue']
            return oid, tag, value

        if 'taglist' not in moduleContext['settings'] or \
                tag not in moduleContext['settings']['taglist']:
            return oid, tag, value

        value = 'initial=%s' % value 

        if context['origValue'].tagSet == rfc1902.TimeTicks.tagSet:
            value += ',rate=100'
        elif context['origValue'].tagSet == rfc1902.Integer.tagSet:
            value += ',rate=0'
 
        return oid, tag + ':numeric', value
            
    # multiple-iteration recording

    if oid not in moduleContext:
        settings = {
            'initial': value
        }
        if context['origValue'].tagSet == rfc1902.TimeTicks.tagSet:
            settings['rate'] = 100
        elif context['origValue'].tagSet == rfc1902.Integer.tagSet:
            settings['rate'] = 0  # may be constants
        if 'addon' in moduleContext['settings']:
            settings.update(
                dict([split(x,'=') for x in moduleContext['settings']['addon']])
            )

        moduleContext[oid] = {}

        moduleContext[oid]['settings'] = settings

    if moduleContext['iterations']:
        if context['stopFlag']: # switching to final iteration
            log.msg('numeric: %s iterations remaining' % moduleContext['settings']['iterations'])
            moduleContext['iterations'] -= 1
            moduleContext['started'] = time.time()
            wait = max(0, float(moduleContext['settings']['period']) - (time.time() - moduleContext['started']))
            raise error.MoreDataNotification(period=wait)
        else:  # storing values on first iteration
            moduleContext[oid]['time'] = time.time()
            moduleContext[oid]['value'] = context['origValue']
            if 'hexvalue' in moduleContext[oid]:
                moduleContext[oid]['hexvalue'] = context['hexvalue']
            if 'hextag' in moduleContext[oid]:
                moduleContext[oid]['hextag'] = context['hextag']
            raise error.NoDataNotification()
    else:
        if context['stopFlag']:
            raise error.NoDataNotification()

        if 'value' in moduleContext[oid]:
            if context['origValue'].tagSet not in (
                        rfc1902.Counter32.tagSet,
                        rfc1902.Counter64.tagSet,
                        rfc1902.TimeTicks.tagSet,
                        rfc1902.Gauge32.tagSet,
                        rfc1902.Integer.tagSet):
                if 'hextag' in moduleContext[oid]:
                    tag = moduleContext[oid]['hextag']
                if 'hexvalue' in moduleContext[oid]:
                    value = moduleContext[oid]['hexvalue']
                return oid, tag, value

            if tag not in moduleContext['settings']['taglist']:
                return oid, tag, moduleContext[oid]['value']
 
            moduleContext[oid]['settings']['rate'] = (int(context['origValue']) - int(moduleContext[oid]['value'])) / (time.time() - moduleContext[oid]['time'])

            tag += ':numeric'
            value = ','.join(
                [ '%s=%s' % (k,v) for k,v in moduleContext[oid]['settings'].items() ]
            )
            return oid, tag, value
        else:
            raise error.NoDataNotification()

def shutdown(**context): pass 
