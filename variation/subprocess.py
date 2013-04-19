# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Get/set managed value by invoking an external program
import sys
import subprocess
from snmpsim import log

moduleOptions = {}

def init(snmpEngine, **context):
    if context['options']:
        moduleOptions.update(
            dict([x.split(':') for x in context['options'].split(',')])
        )
    if 'shell' not in moduleOptions:
        moduleOptions['shell'] = sys.platform[:3] == 'win'
    else:
        moduleOptions['shell'] = int(moduleOptions['shell'])
 
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

    log.msg('subprocess: executing external process "%s"\r\n' % ' '.join(args))

    try:
        return oid, tag, subprocess.check_output(
            args, shell=moduleOptions['shell']
        )
    except subprocess.CalledProcessError:
        log.msg('subprocess: external program execution failed\r\n')
        return context['origOid'], tag, context['errorStatus']

def shutdown(snmpEngine, **context): pass 
