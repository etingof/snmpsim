# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Get/set managed value by invoking an external program
import sys
import subprocess

def init(snmpEngine, *args): pass

def process(oid, tag, value, **context):
    try:
        return oid, subprocess.check_output(
            [ x\
              .replace('@DATAFILE@', context['dataFile'])\
              .replace('@OID@', str(oid))\
              .replace('@TAG@', tag)\
              .replace('@ORIGOID@', str(context['origOid']))\
              .replace('@ORIGTAG@', str(sum([ x for x in context['origValue'].tagSet[0]])))\
              .replace('@ORIGVALUE@', str(context['origValue']))\
              .replace('@SETFLAG@', str(int(context['setFlag'])))\
              .replace('@NEXTFLAG@', str(int(context['nextFlag'])))\
              .replace('@SUBTREEFLAG@', str(int(context['subtreeFlag'])))\
              for x in value.split(' ') ], shell=sys.platform=='win'
        )
    except subprocess.CalledProcessError:
        return context['origOid'], context['errorStatus']

def shutdown(snmpEngine, *args): pass 
