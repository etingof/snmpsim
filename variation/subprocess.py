# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Get/set managed value by invoking an external program
import sys
import subprocess
from pysnmp.proto import rfc1902
from snmpsim.mltsplit import split
from snmpsim import log

def init(**context):
    moduleContext['settings'] = {}
    if context['options']:
        moduleContext['settings'].update(
            dict([split(x, ':') for x in split(context['options'], ',')])
        )
    if 'shell' not in moduleContext['settings']:
        moduleContext['settings']['shell'] = sys.platform[:3] == 'win'
    else:
        moduleContext['settings']['shell'] = int(moduleContext['settings']['shell'])
 
def variate(oid, tag, value, **context):
    # in --v2c-arch some of the items are not defined
    transportDomain = transportAddress = securityModel = securityName = \
                      securityLevel = contextName = '<undefined>'
    if 'transportDomain' in context:
        transportDomain = rfc1902.ObjectName(context['transportDomain']).prettyPrint()
    if 'transportAddress' in context:
        transportAddress = ':'.join([str(x) for x in context['transportAddress']])
    if 'securityModel' in context:
        securityModel = str(context['securityModel'])
    if 'securityName' in context:
        securityName = str(context['securityName'])
    if 'securityLevel' in context:
        securityLevel = str(context['securityLevel'])
    if 'contextName' in context:
        contextName = str(context['contextName'])

    args = [ x\
             .replace('@TRANSPORTDOMAIN@', transportDomain)\
             .replace('@TRANSPORTADDRESS@', transportAddress)\
             .replace('@SECURITYMODEL@', securityModel)\
             .replace('@SECURITYNAME@', securityName)\
             .replace('@SECURITYLEVEL@', securityLevel)\
             .replace('@CONTEXTNAME@', contextName)\
             .replace('@DATAFILE@', context['dataFile'])\
             .replace('@OID@', str(oid))\
             .replace('@TAG@', tag)\
             .replace('@ORIGOID@', str(context['origOid']))\
             .replace('@ORIGTAG@', str(sum([ x for x in context['origValue'].tagSet[0]])))\
             .replace('@ORIGVALUE@', str(context['origValue']))\
             .replace('@SETFLAG@', str(int(context['setFlag'])))\
             .replace('@NEXTFLAG@', str(int(context['nextFlag'])))\
             .replace('@SUBTREEFLAG@', str(int(context['subtreeFlag'])))\
             for x in split(value, ' ') ]

    log.msg('subprocess: executing external process "%s"' % ' '.join(args))

    call = hasattr(subprocess, 'check_output') and subprocess.check_output or \
               hasattr(subprocess, 'check_call') and subprocess.check_call or \
               subprocess.call
    if not hasattr(subprocess, 'check_output'):
        log.msg('subprocess: old Python, expect no output!')

    try:
        return oid, tag, call(
            args, shell=moduleContext['settings']['shell']
        )
    except hasattr(subprocess, 'CalledProcessError') and \
               subprocess.CalledProcessError or Exception:
        log.msg('subprocess: external program execution failed')
        return context['origOid'], tag, context['errorStatus']

def shutdown(**context): pass 
