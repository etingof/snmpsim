#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# Managed value variation module
# Get/set managed value by invoking an external program
#
import subprocess
import sys

from pysnmp.proto import rfc1902

from snmpsim import log
from snmpsim.mltsplit import split


def init(**context):
    moduleContext['settings'] = {}

    if context['options']:
        moduleContext['settings'].update(
            dict([split(x, ':') for x in split(context['options'], ',')]))

    if 'shell' not in moduleContext['settings']:
        moduleContext['settings']['shell'] = sys.platform[:3] == 'win'

    else:
        moduleContext['settings']['shell'] = int(
            moduleContext['settings']['shell'])


def variate(oid, tag, value, **context):
    # in --v2c-arch some of the items are not defined
    transportDomain = transportAddress = securityModel = '<undefined>'
    securityName = securityLevel = contextName = transportDomain

    if 'transportDomain' in context:
        transportDomain = rfc1902.ObjectName(
            context['transportDomain']).prettyPrint()

    if 'transportAddress' in context:
        transportAddress = ':'.join(
            [str(x) for x in context['transportAddress']])

    if 'securityModel' in context:
        securityModel = str(context['securityModel'])

    if 'securityName' in context:
        securityName = str(context['securityName'])

    if 'securityLevel' in context:
        securityLevel = str(context['securityLevel'])

    if 'contextName' in context:
        contextName = str(context['contextName'])

    args = [
        (x
        .replace('@TRANSPORTDOMAIN@', transportDomain)
        .replace('@TRANSPORTADDRESS@', transportAddress)
        .replace('@SECURITYMODEL@', securityModel)
        .replace('@SECURITYNAME@', securityName)
        .replace('@SECURITYLEVEL@', securityLevel)
        .replace('@CONTEXTNAME@', contextName)
        .replace('@DATAFILE@', context['dataFile'])
        .replace('@OID@', str(oid))
        .replace('@TAG@', tag)
        .replace('@ORIGOID@', str(context['origOid']))
        .replace('@ORIGTAG@', str(sum([x for x in context['origValue'].tagSet[0]])))
        .replace('@ORIGVALUE@', str(context['origValue']))
        .replace('@SETFLAG@', str(int(context['setFlag'])))
        .replace('@NEXTFLAG@', str(int(context['nextFlag'])))
        .replace('@SUBTREEFLAG@', str(int(context['subtreeFlag']))))
        for x in split(value, ' ')]

    log.msg('subprocess: executing external process "%s"' % ' '.join(args))

    try:
        handler = subprocess.check_output

    except AttributeError:
        log.msg('subprocess: old Python, expect no output!')

        try:
            handler = subprocess.check_call

        except AttributeError:
            handler = subprocess.call

    try:
        return oid, tag, handler(
            args, shell=moduleContext['settings']['shell'])

    except getattr(subprocess, 'CalledProcessError', Exception):
        log.msg('subprocess: external program execution failed')
        return context['origOid'], tag, context['errorStatus']


def shutdown(**context):
    pass
