#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator: fully-fledged SNMP v1/v2c/v3 command responder
#
import argparse
import functools
import os
import sys
import traceback
from hashlib import md5

from pyasn1 import debug as pyasn1_debug
from pyasn1.compat.octets import null
from pyasn1.type import univ
from pysnmp import debug as pysnmp_debug
from pysnmp import error
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.entity import config
from pysnmp.entity import engine
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.entity.rfc3413 import context

from snmpsim import confdir
from snmpsim import controller
from snmpsim import daemon
from snmpsim import datafile
from snmpsim import endpoints
from snmpsim import log
from snmpsim import utils
from snmpsim import variation
from snmpsim.error import NoDataNotification
from snmpsim.error import SnmpsimError
from snmpsim.reporting.manager import ReportingManager

AUTH_PROTOCOLS = {
    'MD5': config.usmHMACMD5AuthProtocol,
    'SHA': config.usmHMACSHAAuthProtocol,
    'SHA224': config.usmHMAC128SHA224AuthProtocol,
    'SHA256': config.usmHMAC192SHA256AuthProtocol,
    'SHA384': config.usmHMAC256SHA384AuthProtocol,
    'SHA512': config.usmHMAC384SHA512AuthProtocol,
    'NONE': config.usmNoAuthProtocol
}

PRIV_PROTOCOLS = {
  'DES': config.usmDESPrivProtocol,
  '3DES': config.usm3DESEDEPrivProtocol,
  'AES': config.usmAesCfb128Protocol,
  'AES128': config.usmAesCfb128Protocol,
  'AES192': config.usmAesCfb192Protocol,
  'AES192BLMT': config.usmAesBlumenthalCfb192Protocol,
  'AES256': config.usmAesCfb256Protocol,
  'AES256BLMT': config.usmAesBlumenthalCfb256Protocol,
  'NONE': config.usmNoPrivProtocol
}

DESCRIPTION = (
    'SNMP agent simulator: responds to SNMP v1/v2c/v3 requests, variate '
    'responses based on transport addresses, SNMP community name, SNMPv3 '
    'context or via variation modules.')

V3_OPTIONS = ('SNMPv3 options')


def probe_hash_context(responder, snmp_engine):
    """v3arch SNMP context name searcher"""
    execCtx = snmp_engine.observer.getExecutionContext(
        'rfc3412.receiveMessage:request')

    (transport_domain,
     transport_address,
     context_engine_id,
     context_name) = (
        execCtx['transportDomain'],
        execCtx['transportAddress'],
        execCtx['contextEngineId'],
        execCtx['contextName'].prettyPrint()
    )

    if context_engine_id == snmp_engine.snmpEngineID:
        context_engine_id = datafile.SELF_LABEL

    else:
        context_engine_id = context_engine_id.prettyPrint()

    for candidate in datafile.probe_context(
            transport_domain, transport_address,
            context_engine_id, context_name):

        if len(candidate) > 32:
            probed_context_name = md5(candidate).hexdigest()

        else:
            probed_context_name = candidate

        try:
            mib_instrum = responder.snmpContext.getMibInstrum(
                probed_context_name)

        except error.PySnmpError:
            pass

        else:
            log.info(
                'Using %s selected by candidate %s; transport ID %s, '
                'source address %s, context engine ID %s, '
                'community name '
                '"%s"' % (mib_instrum, candidate,
                          univ.ObjectIdentifier(transport_domain),
                          transport_address[0], context_engine_id,
                          probed_context_name))
            context_name = probed_context_name
            break
    else:
        mib_instrum = responder.snmpContext.getMibInstrum(context_name)
        log.info(
            'Using %s selected by contextName "%s", transport ID %s, '
            'source address %s' % (mib_instrum, context_name,
                                   univ.ObjectIdentifier(transport_domain),
                                   transport_address[0]))

    if not isinstance(mib_instrum, (
            controller.MibInstrumController,
            controller.DataIndexInstrumController)):
        log.error(
            'LCD access denied (contextName does not match any data file)')
        raise NoDataNotification()

    return context_name


class GetCommandResponder(cmdrsp.GetCommandResponder):
    """v3arch GET command handler"""

    def handleMgmtOperation(
            self, snmp_engine, state_reference, context_name, pdu, ac_info):
        try:
            cmdrsp.GetCommandResponder.handleMgmtOperation(
                self, snmp_engine, state_reference,
                probe_hash_context(self, snmp_engine),
                pdu, (None, snmp_engine)  # custom acInfo
            )

        except NoDataNotification:
            self.releaseStateInformation(state_reference)


class SetCommandResponder(cmdrsp.SetCommandResponder):
    """v3arch SET command handler"""

    def handleMgmtOperation(
            self, snmp_engine, state_reference, context_name, pdu, ac_info):
        try:
            cmdrsp.SetCommandResponder.handleMgmtOperation(
                self, snmp_engine, state_reference,
                probe_hash_context(self, snmp_engine),
                pdu, (None, snmp_engine)  # custom acInfo
            )

        except NoDataNotification:
            self.releaseStateInformation(state_reference)


class NextCommandResponder(cmdrsp.NextCommandResponder):
    """v3arch GETNEXT command handler"""

    def handleMgmtOperation(
            self, snmp_engine, state_reference, context_name, pdu, ac_info):
        try:
            cmdrsp.NextCommandResponder.handleMgmtOperation(
                self, snmp_engine, state_reference,
                probe_hash_context(self, snmp_engine),
                pdu, (None, snmp_engine)  # custom acInfo
            )

        except NoDataNotification:
            self.releaseStateInformation(state_reference)


class BulkCommandResponder(cmdrsp.BulkCommandResponder):
    """v3arch GETBULK command handler"""

    def handleMgmtOperation(
            self, snmp_engine, state_reference, context_name, pdu, ac_info):
        try:
            cmdrsp.BulkCommandResponder.handleMgmtOperation(
                self, snmp_engine, state_reference,
                probe_hash_context(self, snmp_engine),
                pdu, (None, snmp_engine)  # custom acInfo
            )

        except NoDataNotification:
            self.releaseStateInformation(state_reference)


def _parse_sized_string(arg, min_length=8):
    if len(arg) < min_length:
        raise argparse.ArgumentTypeError(
            'Value "%s" must be %s+ chars of length' % (arg, min_length))

    return arg


def main():

    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        '-v', '--version', action='version',
        version=utils.TITLE)

    parser.add_argument(
        '-h', action='store_true', dest='usage',
        help='Brief usage message')

    parser.add_argument(
        '--help', action='store_true',
        help='Detailed help message')

    parser.add_argument(
        '--quiet', action='store_true',
        help='Do not print out informational messages')

    parser.add_argument(
        '--debug', choices=pysnmp_debug.flagMap,
        action='append', type=str, default=[],
        help='Enable one or more categories of SNMP debugging.')

    parser.add_argument(
        '--debug-asn1', choices=pyasn1_debug.FLAG_MAP,
        action='append', type=str, default=[],
        help='Enable one or more categories of ASN.1 debugging.')

    parser.add_argument(
        '--logging-method', type=lambda x: x.split(':'),
        metavar='=<%s[:args]>]' % '|'.join(log.METHODS_MAP),
        default='stderr', help='Logging method.')

    parser.add_argument(
        '--log-level', choices=log.LEVELS_MAP,
        type=str, default='info', help='Logging level.')

    parser.add_argument(
        '--reporting-method', type=lambda x: x.split(':'),
        metavar='=<%s[:args]>]' % '|'.join(ReportingManager.REPORTERS),
        default='null', help='Activity metrics reporting method.')

    parser.add_argument(
        '--daemonize', action='store_true',
        help='Disengage from controlling terminal and become a daemon')

    parser.add_argument(
        '--process-user', type=str,
        help='If run as root, switch simulator daemon to this user right '
             'upon binding privileged ports')

    parser.add_argument(
        '--process-group', type=str,
        help='If run as root, switch simulator daemon to this group right '
             'upon binding privileged ports')

    parser.add_argument(
        '--pid-file', metavar='<FILE>', type=str,
        default='/var/run/%s/%s.pid' % (__name__, os.getpid()),
        help='SNMP simulation data file to write records to')

    parser.add_argument(
        '--cache-dir', metavar='<DIR>', type=str,
        help='Location for SNMP simulation data file indices to create')

    parser.add_argument(
        '--force-index-rebuild', action='store_true',
        help='Rebuild simulation data files indices even if they seem '
             'up to date')

    parser.add_argument(
        '--validate-data', action='store_true',
        help='Validate simulation data files on daemon start-up')

    parser.add_argument(
        '--variation-modules-dir', metavar='<DIR>', type=str,
        action='append', default=[],
        help='Variation modules search path(s)')

    parser.add_argument(
        '--variation-module-options', metavar='<module[=alias][:args]>',
        type=str, action='append', default=[],
        help='Options for a specific variation module')

    parser.add_argument(
        '--v3-only', action='store_true',
        help='Trip legacy SNMP v1/v2c support to gain a little lesser memory '
             'footprint')

    parser.add_argument(
        '--transport-id-offset', type=int, default=0,
        help='Start numbering the last sub-OID of transport endpoint OIDs '
             'starting from this ID')

    parser.add_argument(
        '--max-var-binds', type=int, default=64,
        help='Maximum number of variable bindings to include in a single '
             'response')

    parser.add_argument(
        '--args-from-file', metavar='<FILE>', type=str,
        help='Read SNMP engine(s) command-line configuration from this '
             'file. Can be useful when command-line is too long')

    # We do not parse SNMP params with argparse, but we want its -h/--help
    snmp_helper = argparse.ArgumentParser(
        description=DESCRIPTION, add_help=False, parents=[parser])

    v3_usage = """\
Configure one or more independent SNMP engines. Each SNMP engine has a
distinct engine ID, its own set of SNMP USM users, one or more network
transport endpoints to listen on and its own simulation data directory.

Each SNMP engine configuration starts with `--v3-engine-id <arg>` parameter
followed by other configuration options up to the next `--v3-engine-id`
option or end of command line

Example
-------

$ snmp-command-responder \\
    --v3-engine-id auto \\
        --data-dir ./data --agent-udpv4-endpoint=127.0.0.1:1024 \\
    --v3-engine-id auto \\
        --data-dir ./data --agent-udpv4-endpoint=127.0.0.1:1025 \\ 
        --data-dir ./data --agent-udpv4-endpoint=127.0.0.1:1026

Besides network endpoints, simulated agents can be addressed by SNMPv1/v2c
community name or SNMPv3 context engine ID/name. These parameters are
configured automatically based on simulation data file paths relative to
`--data-dir`.
"""
    v3_group = snmp_helper.add_argument_group(v3_usage)

    v3_group.add_argument(
        '--v3-engine-id', type=str, metavar='<HEX|auto>', default='auto',
        help='SNMPv3 engine ID')

    v3_group.add_argument(
        '--v3-user', metavar='<STRING>',
        type=functools.partial(_parse_sized_string, min_length=1),
        help='SNMPv3 USM user (security) name')

    v3_group.add_argument(
        '--v3-auth-key', type=_parse_sized_string,
        help='SNMPv3 USM authentication key (must be > 8 chars)')

    v3_group.add_argument(
        '--v3-auth-proto', choices=AUTH_PROTOCOLS,
        type=lambda x: x.upper(), default='NONE',
        help='SNMPv3 USM authentication protocol')

    v3_group.add_argument(
        '--v3-priv-key', type=_parse_sized_string,
        help='SNMPv3 USM privacy (encryption) key (must be > 8 chars)')

    v3_group.add_argument(
        '--v3-priv-proto', choices=PRIV_PROTOCOLS,
        type=lambda x: x.upper(), default='NONE',
        help='SNMPv3 USM privacy (encryption) protocol')

    v3_group.add_argument(
        '--v3-context-engine-id',
        type=lambda x: univ.OctetString(hexValue=x[2:]),
        help='SNMPv3 context engine ID')

    v3_group.add_argument(
        '--v3-context-name', type=str, default='',
        help='SNMPv3 context engine ID')

    v3_group.add_argument(
        '--agent-udpv4-endpoint', type=endpoints.parse_endpoint,
        metavar='<[X.X.X.X]:NNNNN>',
        help='SNMP agent UDP/IPv4 address to listen on (name:port)')

    v3_group.add_argument(
        '--agent-udpv6-endpoint',
        type=functools.partial(endpoints.parse_endpoint, ipv6=True),
        metavar='<[X:X:..X]:NNNNN>',
        help='SNMP agent UDP/IPv6 address to listen on ([name]:port)')

    v3_group.add_argument(
        '--data-dir',
        type=str, metavar='<DIR>',
        help='SNMP simulation data recordings directory.')

    args, unparsed_args = parser.parse_known_args()

    if args.usage:
        snmp_helper.print_usage(sys.stderr)
        return 1

    if args.help:
        snmp_helper.print_help(sys.stderr)
        return 1

    _, unknown_args = snmp_helper.parse_known_args(unparsed_args)
    if unknown_args:
        sys.stderr.write(
            'ERROR: Unknown command-line parameter(s) '
            '%s\r\n' % ' '.join(unknown_args))
        snmp_helper.print_usage(sys.stderr)
        return 1

    # Reformat unparsed args into a list of (option, value) tuples
    snmp_args = []
    name = None

    for opt in unparsed_args:
        if '=' in opt:
            snmp_args.append(opt.split('='))

        elif name:
            snmp_args.append((name, opt))
            name = None

        else:
            name = opt

    if name:
        sys.stderr.write(
            'ERROR: Non-paired command-line key-value parameter '
            '%s\r\n' % name)
        snmp_helper.print_usage(sys.stderr)
        return 1

    if args.cache_dir:
        confdir.cache = args.cache_dir

    if args.variation_modules_dir:
        confdir.variation = args.variation_modules_dir

    variation_modules_options = variation.parse_modules_options(
        args.variation_module_options)

    if args.args_from_file:
        try:
            with open(args.args_from_file) as fl:
                snmp_args.extend([handler.split('=', 1) for handler in fl.read().split()])

        except Exception as exc:
            sys.stderr.write(
                'ERROR: file %s opening failure: '
                '%s\r\n' % (args.args_from_file, exc))
            snmp_helper.print_usage(sys.stderr)
            return 1

    with daemon.PrivilegesOf(args.process_user, args.process_group):

        proc_name = os.path.basename(sys.argv[0])

        try:
            log.set_logger(proc_name, *args.logging_method, force=True)

            if args.log_level:
                log.set_level(args.log_level)

        except SnmpsimError as exc:
            sys.stderr.write('%s\r\n' % exc)
            snmp_helper.print_usage(sys.stderr)
            return 1

        try:
            ReportingManager.configure(*args.reporting_method)

        except SnmpsimError as exc:
            sys.stderr.write('%s\r\n' % exc)
            snmp_helper.print_usage(sys.stderr)
            return 1

    if args.daemonize:
        try:
            daemon.daemonize(args.pid_file)

        except Exception as exc:
            sys.stderr.write(
                'ERROR: cant daemonize process: %s\r\n' % exc)
            snmp_helper.print_usage(sys.stderr)
            return 1

    if not os.path.exists(confdir.cache):
        try:
            with daemon.PrivilegesOf(args.process_user, args.process_group):
                os.makedirs(confdir.cache)

        except OSError as exc:
            log.error('failed to create cache directory "%s": '
                      '%s' % (confdir.cache, exc))
            return 1

        else:
            log.info('Cache directory "%s" created' % confdir.cache)

    variation_modules = variation.load_variation_modules(
        confdir.variation, variation_modules_options)

    with daemon.PrivilegesOf(args.process_user, args.process_group):
        variation.initialize_variation_modules(
            variation_modules, mode='variating')

    def configure_managed_objects(
            data_dirs, data_index_instrum_controller, snmp_engine=None,
            snmp_context=None):
        """Build pysnmp Managed Objects base from data files information"""

        _mib_instrums = {}
        _data_files = {}

        for dataDir in data_dirs:

            log.info(
                'Scanning "%s" directory for %s data '
                'files...' % (dataDir, ','.join(
                    [' *%s%s' % (os.path.extsep, x.ext)
                     for x in variation.RECORD_TYPES.values()])))

            if not os.path.exists(dataDir):
                log.info('Directory "%s" does not exist' % dataDir)
                continue

            log.msg.inc_ident()

            for (full_path,
                 text_parser,
                 community_name) in datafile.get_data_files(dataDir):
                if community_name in _data_files:
                    log.error(
                        'ignoring duplicate Community/ContextName "%s" for data '
                        'file %s (%s already loaded)' % (community_name, full_path,
                                                         _data_files[community_name]))
                    continue

                elif full_path in _mib_instrums:
                    mib_instrum = _mib_instrums[full_path]
                    log.info('Configuring *shared* %s' % (mib_instrum,))

                else:
                    data_file = datafile.DataFile(
                        full_path, text_parser, variation_modules)
                    data_file.index_text(args.force_index_rebuild, args.validate_data)

                    MibController = controller.MIB_CONTROLLERS[data_file.layout]
                    mib_instrum = MibController(data_file)

                    _mib_instrums[full_path] = mib_instrum
                    _data_files[community_name] = full_path

                    log.info('Configuring %s' % (mib_instrum,))

                log.info('SNMPv1/2c community name: %s' % (community_name,))

                agent_name = md5(
                    univ.OctetString(community_name).asOctets()).hexdigest()

                context_name = agent_name

                if not args.v3_only:
                    # snmpCommunityTable::snmpCommunityIndex can't be > 32
                    config.addV1System(
                        snmp_engine, agent_name, community_name,
                        contextName=context_name)

                snmp_context.registerContextName(context_name, mib_instrum)

                if len(community_name) <= 32:
                    snmp_context.registerContextName(community_name, mib_instrum)

                data_index_instrum_controller.add_data_file(
                    full_path, community_name, context_name)

                log.info(
                    'SNMPv3 Context Name: %s'
                    '%s' % (context_name, len(community_name) <= 32 and
                            ' or %s' % community_name or ''))

            log.msg.dec_ident()

        del _mib_instrums
        del _data_files

    # Bind transport endpoints
    for idx, opt in enumerate(snmp_args):
        if opt[0] == '--agent-udpv4-endpoint':
            snmp_args[idx] = (
                opt[0], endpoints.IPv4TransportEndpoints().add(opt[1]))

        elif opt[0] == '--agent-udpv6-endpoint':
            snmp_args[idx] = (
                opt[0], endpoints.IPv6TransportEndpoints().add(opt[1]))

    # Start configuring SNMP engine(s)

    transport_dispatcher = AsyncoreDispatcher()

    transport_dispatcher.registerRoutingCbFun(lambda td, t, d: td)

    if not snmp_args or snmp_args[0][0] != '--v3-engine-id':
        snmp_args.insert(0, ('--v3-engine-id', 'auto'))

    if snmp_args and snmp_args[-1][0] != 'end-of-options':
        snmp_args.append(('end-of-options', ''))

    snmp_engine = None

    transport_index = {
        'udpv4': args.transport_id_offset,
        'udpv6': args.transport_id_offset,
    }

    for opt in snmp_args:

        if opt[0] in ('--v3-engine-id', 'end-of-options'):

            if snmp_engine:

                log.info('--- SNMP Engine configuration')

                log.info(
                    'SNMPv3 EngineID: '
                    '%s' % (hasattr(snmp_engine, 'snmpEngineID')
                            and snmp_engine.snmpEngineID.prettyPrint() or '<unknown>',))

                if not v3_context_engine_ids:
                    v3_context_engine_ids.append((None, []))

                log.msg.inc_ident()

                log.info('--- Simulation data recordings configuration')

                for v3_context_engine_id, ctx_data_dirs in v3_context_engine_ids:
                    snmp_context = context.SnmpContext(snmp_engine, v3_context_engine_id)
                    # unregister default context
                    snmp_context.unregisterContextName(null)

                    log.info(
                        'SNMPv3 Context Engine ID: '
                        '%s' % snmp_context.contextEngineId.prettyPrint())

                    data_index_instrum_controller = controller.DataIndexInstrumController()

                    with daemon.PrivilegesOf(args.process_user, args.process_group):
                        configure_managed_objects(
                            ctx_data_dirs or data_dirs or confdir.data,
                            data_index_instrum_controller,
                            snmp_engine,
                            snmp_context
                        )

                # Configure access to data index

                config.addV1System(snmp_engine, 'index',
                                   'index', contextName='index')

                log.info('--- SNMPv3 USM configuration')

                if not v3_users:
                    v3_users = ['simulator']
                    v3_auth_keys[v3_users[0]] = 'auctoritas'
                    v3_auth_protos[v3_users[0]] = 'MD5'
                    v3_priv_keys[v3_users[0]] = 'privatus'
                    v3_priv_protos[v3_users[0]] = 'DES'

                for v3User in v3_users:
                    if v3User in v3_auth_keys:
                        if v3User not in v3_auth_protos:
                            v3_auth_protos[v3User] = 'MD5'

                    elif v3User in v3_auth_protos:
                        log.error(
                            'auth protocol configured without key for user '
                            '%s' % v3User)
                        return 1

                    else:
                        v3_auth_keys[v3User] = None
                        v3_auth_protos[v3User] = 'NONE'

                    if v3User in v3_priv_keys:
                        if v3User not in v3_priv_protos:
                            v3_priv_protos[v3User] = 'DES'

                    elif v3User in v3_priv_protos:
                        log.error(
                            'privacy protocol configured without key for user '
                            '%s' % v3User)
                        return 1

                    else:
                        v3_priv_keys[v3User] = None
                        v3_priv_protos[v3User] = 'NONE'

                    if (AUTH_PROTOCOLS[v3_auth_protos[v3User]] == config.usmNoAuthProtocol and
                            PRIV_PROTOCOLS[v3_priv_protos[v3User]] != config.usmNoPrivProtocol):
                        log.error(
                            'privacy impossible without authentication for USM user '
                            '%s' % v3User)
                        return 1

                    try:
                        config.addV3User(
                            snmp_engine,
                            v3User,
                            AUTH_PROTOCOLS[v3_auth_protos[v3User]],
                            v3_auth_keys[v3User],
                            PRIV_PROTOCOLS[v3_priv_protos[v3User]],
                            v3_priv_keys[v3User])

                    except error.PySnmpError as exc:
                        log.error(
                            'bad USM values for user %s: '
                            '%s' % (v3User, exc))
                        return 1

                    log.info('SNMPv3 USM SecurityName: %s' % v3User)

                    if AUTH_PROTOCOLS[v3_auth_protos[v3User]] != config.usmNoAuthProtocol:
                        log.info(
                            'SNMPv3 USM authentication key: %s, '
                            'authentication protocol: '
                            '%s' % (v3_auth_keys[v3User], v3_auth_protos[v3User]))

                    if PRIV_PROTOCOLS[v3_priv_protos[v3User]] != config.usmNoPrivProtocol:
                        log.info(
                            'SNMPv3 USM encryption (privacy) key: %s, '
                            'encryption protocol: '
                            '%s' % (v3_priv_keys[v3User], v3_priv_protos[v3User]))

                snmp_context.registerContextName('index', data_index_instrum_controller)

                log.info(
                    'Maximum number of variable bindings in SNMP response: '
                    '%s' % local_max_var_binds)

                log.info('--- Transport configuration')

                if not agent_udpv4_endpoints and not agent_udpv6_endpoints:
                    log.error(
                        'agent endpoint address(es) not specified for SNMP '
                        'engine ID %s' % v3_engine_id)
                    return 1

                for agent_udpv4_endpoint in agent_udpv4_endpoints:
                    transport_domain = udp.domainName + (transport_index['udpv4'],)
                    transport_index['udpv4'] += 1

                    snmp_engine.registerTransportDispatcher(
                        transport_dispatcher, transport_domain)

                    config.addSocketTransport(
                        snmp_engine, transport_domain, agent_udpv4_endpoint[0])

                    log.info(
                        'Listening at UDP/IPv4 endpoint %s, transport ID '
                        '%s' % (agent_udpv4_endpoint[1],
                                '.'.join([str(handler) for handler in transport_domain])))

                for agent_udpv6_endpoint in agent_udpv6_endpoints:
                    transport_domain = udp6.domainName + (transport_index['udpv6'],)
                    transport_index['udpv6'] += 1

                    snmp_engine.registerTransportDispatcher(
                        transport_dispatcher, transport_domain)

                    config.addSocketTransport(
                        snmp_engine,
                        transport_domain, agent_udpv6_endpoint[0])

                    log.info(
                        'Listening at UDP/IPv6 endpoint %s, transport ID '
                        '%s' % (agent_udpv6_endpoint[1],
                                '.'.join([str(handler) for handler in transport_domain])))

                # SNMP applications
                GetCommandResponder(snmp_engine, snmp_context)
                SetCommandResponder(snmp_engine, snmp_context)
                NextCommandResponder(snmp_engine, snmp_context)
                BulkCommandResponder(
                    snmp_engine, snmp_context).maxVarBinds = local_max_var_binds

                log.msg.dec_ident()

                if opt[0] == 'end-of-options':
                    # Load up the rest of MIBs while running privileged
                    (snmp_engine
                     .msgAndPduDsp
                     .mibInstrumController
                     .mibBuilder.loadModules())
                    break

            # Prepare for next engine ID configuration

            v3_context_engine_ids = []
            data_dirs = []
            local_max_var_binds = args.max_var_binds
            v3_users = []
            v3_auth_keys = {}
            v3_auth_protos = {}
            v3_priv_keys = {}
            v3_priv_protos = {}
            agent_udpv4_endpoints = []
            agent_udpv6_endpoints = []

            try:
                v3_engine_id = opt[1]
                if not v3_engine_id or v3_engine_id.lower() == 'auto':
                    snmp_engine = engine.SnmpEngine()

                else:
                    snmp_engine = engine.SnmpEngine(
                        snmpEngineID=univ.OctetString(hexValue=v3_engine_id))

            except Exception as exc:
                log.error(
                    'SNMPv3 Engine initialization failed, EngineID "%s": '
                    '%s' % (v3_engine_id, exc))
                return 1

            config.addContext(snmp_engine, '')

        elif opt[0] == '--v3-context-engine-id':
            v3_context_engine_ids.append((univ.OctetString(hexValue=opt[1]), []))

        elif opt[0] == '--data-dir':
            if v3_context_engine_ids:
                v3_context_engine_ids[-1][1].append(opt[1])

            else:
                data_dirs.append(opt[1])

        elif opt[0] == '--max-varbinds':
            local_max_var_binds = opt[1]

        elif opt[0] == '--v3-user':
            v3_users.append(opt[1])

        elif opt[0] == '--v3-auth-key':
            if not v3_users:
                log.error('--v3-user should precede %s' % opt[0])
                return 1

            if v3_users[-1] in v3_auth_keys:
                log.error(
                    'repetitive %s option for user %s' % (opt[0], v3_users[-1]))
                return 1

            v3_auth_keys[v3_users[-1]] = opt[1]

        elif opt[0] == '--v3-auth-proto':
            if opt[1].upper() not in AUTH_PROTOCOLS:
                log.error('bad v3 auth protocol %s' % opt[1])
                return 1

            else:
                if not v3_users:
                    log.error('--v3-user should precede %s' % opt[0])
                    return 1

                if v3_users[-1] in v3_auth_protos:
                    log.error(
                        'repetitive %s option for user %s' % (opt[0], v3_users[-1]))
                    return 1

                v3_auth_protos[v3_users[-1]] = opt[1].upper()

        elif opt[0] == '--v3-priv-key':
            if not v3_users:
                log.error('--v3-user should precede %s' % opt[0])
                return 1

            if v3_users[-1] in v3_priv_keys:
                log.error(
                    'repetitive %s option for user %s' % (opt[0], v3_users[-1]))
                return 1

            v3_priv_keys[v3_users[-1]] = opt[1]

        elif opt[0] == '--v3-priv-proto':
            if opt[1].upper() not in PRIV_PROTOCOLS:
                log.error('bad v3 privacy protocol %s' % opt[1])
                return 1

            else:
                if not v3_users:
                    log.error('--v3-user should precede %s' % opt[0])
                    return 1

                if v3_users[-1] in v3_priv_protos:
                    log.error(
                        'repetitive %s option for user %s' % (opt[0], v3_users[-1]))
                    return 1

                v3_priv_protos[v3_users[-1]] = opt[1].upper()

        elif opt[0] == '--agent-udpv4-endpoint':
            agent_udpv4_endpoints.append(opt[1])

        elif opt[0] == '--agent-udpv6-endpoint':
            agent_udpv6_endpoints.append(opt[1])

    transport_dispatcher.jobStarted(1)  # server job would never finish

    with daemon.PrivilegesOf(args.process_user, args.process_group, final=True):

        try:
            transport_dispatcher.runDispatcher()

        except KeyboardInterrupt:
            log.info('Shutting down process...')

        finally:
            if variation_modules:
                log.info('Shutting down variation modules:')

                for name, contexts in variation_modules.items():
                    body = contexts[0]
                    try:
                        body['shutdown'](options=body['args'], mode='variation')

                    except Exception as exc:
                        log.error(
                            'Variation module "%s" shutdown FAILED: '
                            '%s' % (name, exc))

                    else:
                        log.info('Variation module "%s" shutdown OK' % name)

            transport_dispatcher.closeDispatcher()

            log.info('Process terminated')

    return 0


if __name__ == '__main__':
    try:
        rc = main()

    except KeyboardInterrupt:
        sys.stderr.write('shutting down process...')
        rc = 0

    except Exception as exc:
        sys.stderr.write('process terminated: %s' % exc)

        for line in traceback.format_exception(*sys.exc_info()):
            sys.stderr.write(line.replace('\n', ';'))
        rc = 1

    sys.exit(rc)
