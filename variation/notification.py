# SNMP Simulator, http://snmpsim.sourceforge.net
# Managed value variation module
# Send SNMP Notification
from pysnmp.hlapi.asyncore import *
from snmpsim.grammar.snmprec import SnmprecGrammar
from snmpsim.mltsplit import split
from snmpsim import error, log

def init(**context): pass

typeMap = {
    's': OctetString,
    'i': Integer32,
    'o': ObjectIdentifier,
    'a': IpAddress,
    'u': Unsigned32,
    'g': Gauge32,
    't': TimeTicks,
    'b': Bits,
    'I': Counter64
}

def _cbFun(sendRequestHandle,
          errorIndication,
          errorStatus, errorIndex,
          varBinds,
          cbCtx):
    oid, value = cbCtx
    if errorIndication or errorStatus:
        log.msg('notification: for %s=%r failed with errorIndication %s, errorStatus %s' % (oid, value, errorIndication, errorStatus))

def variate(oid, tag, value, **context):
    if 'snmpEngine' in context and context['snmpEngine']:
        snmpEngine = context['snmpEngine']
        if snmpEngine not in moduleContext:
            moduleContext[snmpEngine] = {}
        if context['transportDomain'] not in moduleContext[snmpEngine]:
            # register this SNMP Engine to handle our transports'
            # receiver IDs (which we build by outbound and simulator
            # transportDomains concatenation)
            snmpEngine.registerTransportDispatcher(
                snmpEngine.transportDispatcher,
                UdpTransportTarget.transportDomain + \
                    context['transportDomain']
            )
            snmpEngine.registerTransportDispatcher(
                snmpEngine.transportDispatcher,
                Udp6TransportTarget.transportDomain + \
                    context['transportDomain']
            )
            moduleContext[snmpEngine][context['transportDomain']] = 1
    else:
        raise error.SnmpsimError('variation module not given snmpEngine')

    if not context['nextFlag'] and not context['exactMatch']:
        return context['origOid'], tag, context['errorStatus']

    if 'settings' not in recordContext:
        recordContext['settings'] = dict([split(x, '=') for x in split(value, ',')])
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
            recordContext['settings']['vlist'] = split(recordContext['settings']['vlist'], ':')
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
            authData = CommunityData(args['community'], mpModel=args['version'] == '2c' and 1 or 0)
        elif args['version'] == '3':
            if args['authproto'] == 'md5':
                authProtocol = usmHMACMD5AuthProtocol
            elif args['authproto'] == 'sha':
                authProtocol = usmHMACSHAAuthProtocol
            elif args['authproto'] == 'none':
                authProtocol = usmNoAuthProtocol
            else:
                log.msg('notification: unknown auth proto %s' % args['authproto'])
                return context['origOid'], tag, context['errorStatus']
            if args['privproto'] == 'des':
                privProtocol = usmDESPrivProtocol
            elif args['privproto'] == 'aes':
                privProtocol = usmAesCfb128Protocol
            elif args['privproto'] == 'none':
                privProtocol = usmNoPrivProtocol
            else:
                log.msg('notification: unknown privacy proto %s' % args['privproto'])
                return context['origOid'], tag, context['errorStatus']
            authData = UsmUserData(args['user'], args['authkey'], args['privkey'], authProtocol=authProtocol, privProtocol=privProtocol)
        else:
            log.msg('notification: unknown SNMP version %s' % args['version'])
            return context['origOid'], tag, context['errorStatus']

        if 'host' not in args:
            log.msg('notification: target hostname not configured for OID' % (oid,))
            return context['origOid'], tag, context['errorStatus']
        
        if args['proto'] == 'udp':
            target = UdpTransportTarget((args['host'], int(args['port'])))
        elif args['proto'] == 'udp6':
            target = Udp6TransportTarget((args['host'], int(args['port'])))
        else:
            log.msg('notification: unknown transport %s' % args['proto'])
            return context['origOid'], tag, context['errorStatus']
       
        localAddress = None

        if 'bindaddr' in args:
            localAddress = args['bindaddr']
        else:
            if context['transportDomain'][:len(target.transportDomain)] == \
                        target.transportDomain:
                localAddress = snmpEngine.transportDispatcher.getTransport(context['transportDomain']).getLocalAddress()[0]
            else:
                log.msg('notification: incompatible network transport types used by CommandResponder vs NotificationOriginator')
                if 'bindaddr' in args:
                    localAddress = args['bindaddr']

        if localAddress:
            log.msg('notification: binding to local address %s' % localAddress)
            target.setLocalAddress((localAddress, 0))

        # this will make target objects different based on their bind address 
        target.transportDomain = target.transportDomain + \
                                 context['transportDomain']

        varBinds = []

        if 'uptime' in args:
            varBinds.append(
                ( ObjectIdentifier('1.3.6.1.2.1.1.3.0'),
                  TimeTicks(args['uptime']) )
            )

        if args['version'] == '1':
            if 'agentaddress' in args:
                varBinds.append(
                    ( ObjectIdentifier('1.3.6.1.6.3.18.1.3.0'),
                      IpAddress(args['agentaddress']) )
                )
            if 'enterprise' in args:
                varBinds.append(
                    ( ObjectIdentifier('1.3.6.1.6.3.1.1.4.3.0'),
                      ObjectIdentifier(args['enterprise']) )
                )

        if 'varbinds' in args:
            vbs = split(args['varbinds'], ':') 
            while vbs:
                varBinds.append(
                    (ObjectIdentifier(vbs[0]), typeMap[vbs[1]](vbs[2]))
                )
                vbs = vbs[3:]

        sendNotification(
            snmpEngine, authData, target, ContextData(), args['ntftype'],
            NotificationType(ObjectIdentity(args['trapoid'])).addVarBinds(*varBinds),
            cbFun=_cbFun, cbCtx=(oid, value)
        )

        log.msg('notification: sending Notification to %s with credentials %s' % (authData, target))

    if context['setFlag'] or 'value' not in args:
        return oid, tag, context['origValue']
    else:
        return oid, tag, args['value']

def shutdown(**context): pass 
