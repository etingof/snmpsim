# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Send SNMP Notification
import sys
from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim import error, log

def init(snmpEngine, **context):
    global ntfOrg
    if snmpEngine:
        ntfOrg = ntforg.AsynNotificationOriginator(snmpEngine)
    else:
        ntfOrg = None

typeMap = {
    's': rfc1902.OctetString,
    'i': rfc1902.Integer32,
    'o': rfc1902.ObjectName,
    'a': rfc1902.IpAddress,
    'u': rfc1902.Unsigned32,
    'g': rfc1902.Gauge32,
    't': rfc1902.TimeTicks,
    'b': rfc1902.Bits,
    'I': rfc1902.Counter64
}

def _cbFun(sendRequestHandle,
          errorIndication,
          errorStatus, errorIndex,
          varBinds,
          cbCtx):
    if errorIndication or errorStatus:
        oid, value = cbCtx
        log.msg('notification: for %s=%r failed with errorIndication %s, errorStatus %s' % (oid, value, errorIndication, errorStatus))

def variate(oid, tag, value, **context):
    if ntfOrg is None:
        raise error.SnmpsimError('variation module not initialized')

    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if 'settings' not in recordContext:
        recordContext['settings'] = dict([ x.split('=') for x in value.split(',') ])
        for k,v in ( ('op', 'set'),
                     ('community', 'public'),
                     ('authkey', None),
                     ('authproto', 'md5'),
                     ('privkey', None),
                     ('privproto', 'des'),
                     ('proto', 'udp'),
                     ('port', '162'),
                     ('ntftype', 'trap'),
                     ('trapoid', '1.3.6.1.6.3.1.1.5.1') ):
            recordContext['settings'].setdefault(k, v)

        if 'hexvalue' in recordContext['settings']:
            recordContext['settings']['value'] = [int(recordContext['settings']['hexvalue'][x:x+2], 16) for x in range(0, len(recordContext['settings']['hexvalue']), 2)]

        if 'vlist' in recordContext['settings']:
            vlist = {}
            recordContext['settings']['vlist'] = recordContext['settings']['vlist'].split(':')
            while recordContext['settings']['vlist']:
                o,v = recordContext['settings']['vlist'][:2]
                recordContext['settings']['vlist'] = recordContext['settings']['vlist'][2:]
                v = SnmprecGrammar.tagMap[tag](v)
                if o not in vlist:
                    vlist[o] = set()
                if o == 'eq':
                    vlist[o].add(v)
                elif o in ('lt', 'gt'):
                    vlist[o] = v
                else:
                    log.msg('notification: bad vlist syntax: %s' % recordContext['settings']['vlist'])
            recordContext['settings']['vlist'] = vlist

    args = recordContext['settings']
   
    if context['setFlag'] and 'vlist' in args:
        if 'eq' in args['vlist'] and  \
                 context['origValue'] in args['vlist']['eq']:
            pass
        elif 'lt' in args['vlist'] and  \
                 context['origValue'] < args['vlist']['lt']:
            pass
        elif 'gt' in args['vlist'] and  \
                 context['origValue'] > args['vlist']['gt']:
            pass
        else:
            return oid, tag, context['origValue']

    if args['op'] not in ('get', 'set', 'any', '*'):
        log.msg('notification: unknown SNMP request type configured: %s' % args['op'])
        return context['origOid'], tag, context['errorStatus']

    if args['op'] == 'get' and not context['setFlag'] or \
       args['op'] == 'set' and context['setFlag'] or \
       args['op'] in ('any', '*'):
        if args['version'] in ('1', '2c'):
            authData = ntforg.CommunityData(args['community'], args['version'] == '2c' and 1 or 0)
        elif args['version'] == '3':
            if args['authproto'] == 'md5':
                authProtocol = ntforg.usmHMACMD5AuthProtocol
            elif args['authproto'] == 'sha':
                authProtocol = ntforg.usmHMACSHAAuthProtocol
            elif args['authproto'] == 'none':
                authProtocol = ntforg.usmNoAuthProtocol
            else:
                log.msg('notification: unknown auth proto %s' % args['authproto'])
                return context['origOid'], tag, context['errorStatus']
            if args['privproto'] == 'des':
                privProtocol = ntforg.usmDESPrivProtocol
            elif args['privproto'] == 'aes':
                privProtocol = ntforg.usmAesCfb128Protocol
            elif args['privproto'] == 'none':
                privProtocol = ntforg.usmNoPrivProtocol
            else:
                log.msg('notification: unknown privacy proto %s' % args['privproto'])
                return context['origOid'], tag, context['errorStatus']
            authData = ntforg.UsmUserData(args['user'], args['authkey'], args['privkey'], authProtocol=authProtocol, privProtocol=privProtocol)
        else:
            log.msg('notification: unknown SNMP version %s' % args['version'])
            return context['origOid'], tag, context['errorStatus']

        if 'host' not in args:
            log.msg('notification: target hostname not configured for OID' % (oid,))
            return context['origOid'], tag, context['errorStatus']

        if args['proto'] == 'udp':
            target = ntforg.UdpTransportTarget((args['host'], int(args['port'])))
        elif args['proto'] == 'udp6':
            target = ntforg.Udp6TransportTarget((args['host'], int(args['port'])))
        else:
            log.msg('notification: unknown transport %s' % args['proto'])
            return context['origOid'], tag, context['errorStatus']

        varBinds = []

        if 'uptime' in args:
            varBinds.append(
                ( rfc1902.ObjectName('1.3.6.1.2.1.1.3.0'),
                  rfc1902.TimeTicks(args['uptime']) )
            )

        if args['version'] == '1':
            if 'agentaddress' in args:
                varBinds.append(
                    ( rfc1902.ObjectName('1.3.6.1.6.3.18.1.3.0'),
                      rfc1902.IpAddress(args['agentaddress']) )
                )
            if 'enterprise' in args:
                varBinds.append(
                    ( rfc1902.ObjectName('1.3.6.1.6.3.1.1.4.3.0'),
                      rfc1902.ObjectName(args['enterprise']) )
                )

        if 'varbinds' in args:
            vbs = args['varbinds'].split(':') 
            while vbs:
                varBinds.append(
                    (rfc1902.ObjectName(vbs[0]), typeMap[vbs[1]](vbs[2]))
                )
                vbs = vbs[3:]

        ntfOrg.sendNotification(
            authData, target, args['ntftype'],
            rfc1902.ObjectName(args['trapoid']),
            varBinds, cbInfo=(_cbFun, (oid, value))
        )

        log.msg('notification: sending Notification to %s with credentials %s' % (authData, target))

    if context['setFlag'] or 'value' not in args:
        return oid, tag, context['origValue']
    else:
        return oid, tag, args['value']

def shutdown(snmpEngine, **context): pass 
