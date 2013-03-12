# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Send SNMP Notification

import sys
from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

settingsCache = {}

def init(snmpEngine, *args):
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
        sys.stdout.write('notification: for %s=%r failed with errorIndication %s, errorStatus %s\r\n' % (oid, value, errorIndication, errorStatus))

def process(oid, tag, value, **context):
    if ntfOrg is None:
        raise Exception('variation module not initialized')
    if not context['exactMatch']:
        return context['origOid'], context['errorStatus']  # serve exact OIDs

    if oid not in settingsCache:
        settingsCache[oid] = dict([ x.split('=') for x in value.split(',') ])
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
            settingsCache[oid].setdefault(k, v)

        if 'hexvalue' in settingsCache[oid]:
            settingsCache[oid]['value'] = [int(settingsCache[oid]['hexvalue'][x:x+2], 16) for x in range(0, len(settingsCache[oid]['hexvalue']), 2)]

    args = settingsCache[oid]
    
    if args['op'] not in ('get', 'set', 'any', '*'):
        sys.stdout.write('notification: unknown SNMP request type configured: %s\r\n' % args['op'])
        return context['origOid'], context['errorStatus']

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
                sys.stdout.write('notification: unknown auth proto %s\r\n' % args['authproto'])
                return context['origOid'], context['errorStatus']
            if args['privproto'] == 'des':
                privProtocol = ntforg.usmDESPrivProtocol
            elif args['privproto'] == 'aes':
                privProtocol = ntforg.usmAesCfb128Protocol
            elif args['privproto'] == 'none':
                privProtocol = ntforg.usmNoPrivProtocol
            else:
                sys.stdout.write('notification: unknown privacy proto %s\r\n' % args['privproto'])
                return context['origOid'], context['errorStatus']
            authData = ntforg.UsmUserData(args['user'], args['authkey'], args['privkey'], authProtocol=authProtocol, privProtocol=privProtocol)
        else:
            sys.stdout.write('notification: unknown SNMP version %s\r\n' % args['version'])
            return context['origOid'], context['errorStatus']

        if 'host' not in args:
            sys.stdout.write('notification: target hostname not configured for OID\r\n' % (oid,))
            return context['origOid'], context['errorStatus']

        if args['proto'] == 'udp':
            target = ntforg.UdpTransportTarget((args['host'], int(args['port'])))
        elif args['proto'] == 'udp6':
            target = ntforg.Udp6TransportTarget((args['host'], int(args['port'])))
        else:
            sys.stdout.write('notification: unknown transport %s\r\n' % args['proto'])
            return context['origOid'], context['errorStatus']

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

    if 'value' in args:
        return oid, args['value']
    else:
        return oid, context['origValue']

def shutdown(snmpEngine, *args): pass 
