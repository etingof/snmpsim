# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Get/set managed value by invoking an external program
import sys
import subprocess
from snmpsim import log

def init(snmpEngine, **context):
    moduleContext['settings'] = {}
    if context['options']:
        moduleContext['settings'].update(
            dict([x.split(':') for x in context['options'].split(',')])
        )
    if 'shell' not in moduleContext['settings']:
        moduleContext['settings']['shell'] = sys.platform[:3] == 'win'
    else:
        moduleContext['settings']['shell'] = int(moduleContext['settings']['shell'])
 
def variate(oid, tag, value, **context):
    args = [ x\
             .replace('@DATAFILE@', context['dataFile'])\
             .replace('@OID@', str(oid))\
             .replace('@TAG@', tag)\
             .replace('@ORIGOID@', str(context['origOid']))\
             .replace('@ORIGTAG@', str(sum([ x for x in context['origValue'].tagSet[0]])))\
             .replace('@ORIGVALUE@', str(context['origValue']))\
             .replace('@SETFLAG@', str(int(context['setFlag'])))\
             .replace('@NEXTFLAG@', str(int(context['nextFlag'])))\
             .replace('@SUBTREEFLAG@', str(int(context['subtreeFlag'])))\
             for x in value.split(' ') ]

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

def shutdown(snmpEngine, **context): pass 
