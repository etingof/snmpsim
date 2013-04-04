# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Simulate request processing delay
import sys
import time
import random
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim import error

settingsCache = {}

def init(snmpEngine, **context):
    random.seed()

def variate(oid, tag, value, **context):
    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if oid not in settingsCache:
        settingsCache[oid] = dict([x.split('=') for x in value.split(',')])

        if 'hexvalue' in settingsCache[oid]:
            settingsCache[oid]['value'] = [int(settingsCache[oid]['hexvalue'][x:x+2], 16) for x in range(0, len(settingsCache[oid]['hexvalue']), 2)]

        if 'wait' in settingsCache[oid]:
            settingsCache[oid]['wait'] = float(settingsCache[oid]['wait'])
        else:
            settingsCache[oid]['wait'] = 500.0

        if 'deviation' in settingsCache[oid]:
            settingsCache[oid]['deviation'] = float(settingsCache[oid]['deviation'])
        else:
            settingsCache[oid]['deviation'] = 0.0

        if 'vlist' in settingsCache[oid]:
            vlist = {}
            settingsCache[oid]['vlist'] = settingsCache[oid]['vlist'].split(':')
            while settingsCache[oid]['vlist']:
                o,v,d = settingsCache[oid]['vlist'][:3]
                settingsCache[oid]['vlist'] = settingsCache[oid]['vlist'][3:]
                d = int(d)
                v = SnmprecGrammar.tagMap[tag](v)
                if o not in vlist:
                    vlist[o] = {}
                if o == 'eq':
                    vlist[o][v] = d
                elif o in ('lt', 'gt'):
                    vlist[o] = v,d
                else:
                    sys.stdout.write('delay: bad vlist syntax: %s\r\n' % settingsCache[oid]['vlist'])
            settingsCache[oid]['vlist'] = vlist

        if 'tlist' in settingsCache[oid]:
            tlist = {}
            settingsCache[oid]['tlist'] = settingsCache[oid]['tlist'].split(':')
            while settingsCache[oid]['tlist']:
                o,v,d = settingsCache[oid]['tlist'][:3]
                settingsCache[oid]['tlist'] = settingsCache[oid]['tlist'][3:]
                v = int(v); d = int(d)
                if o not in tlist:
                    tlist[o] = {}
                if o == 'eq':
                    tlist[o][v] = d
                elif o in ('lt', 'gt'):
                    tlist[o] = v,d
                else:
                    sys.stdout.write('delay: bad tlist syntax: %s\r\n' % settingsCache[oid]['tlist'])
            settingsCache[oid]['tlist'] = tlist

    if context['setFlag'] and 'vlist' in settingsCache[oid]:
        if 'eq' in settingsCache[oid]['vlist'] and  \
                 context['origValue'] in settingsCache[oid]['vlist']['eq']:
            delay = settingsCache[oid]['vlist']['eq'][context['origValue']]
        elif 'lt' in settingsCache[oid]['vlist'] and  \
                 context['origValue'] < settingsCache[oid]['vlist']['lt'][0]:
            delay = settingsCache[oid]['vlist']['lt'][1]
        elif 'gt' in settingsCache[oid]['vlist'] and  \
                 context['origValue'] > settingsCache[oid]['vlist']['gt'][0]:
            delay = settingsCache[oid]['vlist']['gt'][1]
        else:
            delay = settingsCache[oid]['wait']

    elif 'tlist' in settingsCache[oid]:
        now = int(time.time())
        if 'eq' in settingsCache[oid]['tlist'] and \
                now == settingsCache[oid]['tlist']['eq']:
            delay = settingsCache[oid]['tlist']['eq'][now]
        elif 'lt' in settingsCache[oid]['tlist'] and  \
                now < settingsCache[oid]['tlist']['lt'][0]:
            delay = settingsCache[oid]['tlist']['lt'][1]
        elif 'gt' in settingsCache[oid]['tlist'] and  \
                now > settingsCache[oid]['tlist']['gt'][0]:
            delay = settingsCache[oid]['tlist']['gt'][1]
        else:
            delay = settingsCache[oid]['wait']
    else:
        delay = settingsCache[oid]['wait']

    if settingsCache[oid]['deviation']:
        delay += random.randrange(
            -settingsCache[oid]['deviation'], settingsCache[oid]['deviation']
        )

    if delay < 0:
        delay = 0
    elif delay > 99999:
        raise error.NoDataNotification()

    time.sleep(delay/1000)  # ms

    if context['setFlag'] or 'value' not in settingsCache[oid]:
        return oid, tag, context['origValue']
    else:
        return oid, tag, settingsCache[oid]['value']

def record(oid, tag, value, **context):
    if context['stopFlag']:
        raise error.NoDataNotification()

    tag += ':delay'
    if 'hexvalue' in context:
        textValue = 'hexvalue=' + context['hexvalue']
    else:
        textValue = 'value=' + value
    textValue += ',wait=%d' % int((time.time()-context['reqTime']) * 1000)  # ms
    if 'options' in context:
        textValue += ',' + context['options']
    return oid, tag, textValue

def shutdown(snmpEngine, **context): pass 
