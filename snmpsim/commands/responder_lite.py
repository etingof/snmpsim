
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator: lightweight SNMP v1/v2c command responder
#
import argparse
import os
import sys
import traceback

from pyasn1 import debug as pyasn1_debug
from pyasn1.codec.ber import decoder
from pyasn1.codec.ber import encoder
from pyasn1.type import univ
from pysnmp import debug as pysnmp_debug
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.proto import api
from pysnmp.proto import rfc1902
from pysnmp.proto import rfc1905

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

SNMP_2TO1_ERROR_MAP = {
    rfc1902.Counter64.tagSet: 5,
    rfc1905.NoSuchObject.tagSet: 2,
    rfc1905.NoSuchInstance.tagSet: 2,
    rfc1905.EndOfMibView.tagSet: 2
}

DESCRIPTION = (
    'Lightweight SNMP agent simulator: responds to SNMP v1/v2c requests, '
    'variate responses based on transport addresses, SNMP community name '
    'or via variation modules.')


def main():

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument(
        '-v', '--version', action='version',
        version=utils.TITLE)

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
        '--v2c-arch', action='store_true',
        help='Use lightweight, legacy SNMP architecture capable to support '
             'v1/v2c versions of SNMP')

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
        '--data-dir', type=str, action='append', metavar='<DIR>',
        dest='data_dirs',
        help='SNMP simulation data recordings directory.')

    endpoint_group = parser.add_mutually_exclusive_group(required=True)

    endpoint_group.add_argument(
        '--agent-udpv4-endpoint', type=str,
        action='append', metavar='<[X.X.X.X]:NNNNN>',
        dest='agent_udpv4_endpoints', default=[],
        help='SNMP agent UDP/IPv4 address to listen on (name:port)')

    endpoint_group.add_argument(
        '--agent-udpv6-endpoint', type=str,
        action='append', metavar='<[X:X:..X]:NNNNN>',
        dest='agent_udpv6_endpoints', default=[],
        help='SNMP agent UDP/IPv6 address to listen on ([name]:port)')

    args = parser.parse_args()

    if args.cache_dir:
        confdir.cache = args.cache_dir

    if args.variation_modules_dir:
        confdir.variation = args.variation_modules_dir

    variation_modules_options = variation.parse_modules_options(
        args.variation_module_options)

    with daemon.PrivilegesOf(args.process_user, args.process_group):

        proc_name = os.path.basename(sys.argv[0])

        try:
            log.set_logger(proc_name, *args.logging_method, force=True)

            if args.log_level:
                log.set_level(args.log_level)

        except SnmpsimError as exc:
            sys.stderr.write('%s\r\n' % exc)
            parser.print_usage(sys.stderr)
            return 1

        try:
            ReportingManager.configure(*args.reporting_method)

        except SnmpsimError as exc:
            sys.stderr.write('%s\r\n' % exc)
            parser.print_usage(sys.stderr)
            return 1

    if args.daemonize:
        try:
            daemon.daemonize(args.pid_file)

        except Exception as exc:
            sys.stderr.write(
                'ERROR: cant daemonize process: %s\r\n' % exc)
            parser.print_usage(sys.stderr)
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

                contexts[univ.OctetString(community_name)] = mib_instrum

                data_index_instrum_controller.add_data_file(
                    full_path, community_name
                )

            log.msg.dec_ident()

        del _mib_instrums
        del _data_files

    def get_bulk_handler(
            req_var_binds, non_repeaters, max_repetitions, read_next_vars):
        """Only v2c arch GETBULK handler"""
        N = min(int(non_repeaters), len(req_var_binds))
        M = int(max_repetitions)
        R = max(len(req_var_binds) - N, 0)

        if R:
            M = min(M, args.max_var_binds / R)

        if N:
            rsp_var_binds = read_next_vars(req_var_binds[:N])

        else:
            rsp_var_binds = []

        var_binds = req_var_binds[-R:]

        while M and R:
            rsp_var_binds.extend(read_next_vars(var_binds))
            var_binds = rsp_var_binds[-R:]
            M -= 1

        return rsp_var_binds

    def commandResponderCbFun(
            transport_dispatcher, transport_domain, transport_address,
            whole_msg):
        """v2c arch command responder request handling callback"""
        while whole_msg:
            msg_ver = api.decodeMessageVersion(whole_msg)

            if msg_ver in api.protoModules:
                p_mod = api.protoModules[msg_ver]

            else:
                log.error('Unsupported SNMP version %s' % (msg_ver,))
                return

            req_msg, whole_msg = decoder.decode(whole_msg, asn1Spec=p_mod.Message())

            community_name = req_msg.getComponentByPosition(1)

            for candidate in datafile.probe_context(
                    transport_domain, transport_address,
                    context_engine_id=datafile.SELF_LABEL,
                    context_name=community_name):
                if candidate in contexts:
                    log.info(
                        'Using %s selected by candidate %s; transport ID %s, '
                        'source address %s, context engine ID <empty>, '
                        'community name '
                        '"%s"' % (contexts[candidate], candidate,
                                  univ.ObjectIdentifier(transport_domain),
                                  transport_address[0], community_name))
                    community_name = candidate
                    break

            else:
                log.error(
                    'No data file selected for transport ID %s, source '
                    'address %s, community name '
                    '"%s"' % (univ.ObjectIdentifier(transport_domain),
                              transport_address[0], community_name))
                return whole_msg

            rsp_msg = p_mod.apiMessage.getResponse(req_msg)
            rsp_pdu = p_mod.apiMessage.getPDU(rsp_msg)
            req_pdu = p_mod.apiMessage.getPDU(req_msg)

            if req_pdu.isSameTypeWith(p_mod.GetRequestPDU()):
                backend_fun = contexts[community_name].readVars

            elif req_pdu.isSameTypeWith(p_mod.SetRequestPDU()):
                backend_fun = contexts[community_name].writeVars

            elif req_pdu.isSameTypeWith(p_mod.GetNextRequestPDU()):
                backend_fun = contexts[community_name].readNextVars

            elif (hasattr(p_mod, 'GetBulkRequestPDU') and
                  req_pdu.isSameTypeWith(p_mod.GetBulkRequestPDU())):

                if not msg_ver:
                    log.info(
                        'GETBULK over SNMPv1 from %s:%s' % (
                            transport_domain, transport_address))
                    return whole_msg

                def backend_fun(var_binds):
                    return get_bulk_handler(
                        var_binds, p_mod.apiBulkPDU.getNonRepeaters(req_pdu),
                        p_mod.apiBulkPDU.getMaxRepetitions(req_pdu),
                        contexts[community_name].readNextVars
                    )

            else:
                log.error(
                    'Unsupported PDU type %s from '
                    '%s:%s' % (req_pdu.__class__.__name__, transport_domain,
                               transport_address))
                return whole_msg

            try:
                var_binds = backend_fun(p_mod.apiPDU.getVarBinds(req_pdu))

            except NoDataNotification:
                return whole_msg

            except Exception as exc:
                log.error('Ignoring SNMP engine failure: %s' % exc)
                return whole_msg

            if not msg_ver:

                for idx in range(len(var_binds)):

                    oid, val = var_binds[idx]

                    if val.tagSet in SNMP_2TO1_ERROR_MAP:
                        var_binds = p_mod.apiPDU.getVarBinds(req_pdu)

                        p_mod.apiPDU.setErrorStatus(
                            rsp_pdu, SNMP_2TO1_ERROR_MAP[val.tagSet])
                        p_mod.apiPDU.setErrorIndex(
                            rsp_pdu, idx + 1)

                        break

            p_mod.apiPDU.setVarBinds(rsp_pdu, var_binds)

            transport_dispatcher.sendMessage(
                encoder.encode(rsp_msg), transport_domain, transport_address)

        return whole_msg

    # Configure access to data index

    log.info('Maximum number of variable bindings in SNMP '
             'response: %s' % args.max_var_binds)

    data_index_instrum_controller = controller.DataIndexInstrumController()

    contexts = {univ.OctetString('index'): data_index_instrum_controller}

    with daemon.PrivilegesOf(args.process_user, args.process_group):
        configure_managed_objects(
            args.data_dirs or confdir.data, data_index_instrum_controller)

    contexts['index'] = data_index_instrum_controller

    # Configure socket server
    transport_dispatcher = AsyncoreDispatcher()

    transport_index = args.transport_id_offset
    for agent_udpv4_endpoint in args.agent_udpv4_endpoints:
        transport_domain = udp.domainName + (transport_index,)
        transport_index += 1

        agent_udpv4_endpoint = (
            endpoints.IPv4TransportEndpoints().add(agent_udpv4_endpoint))

        transport_dispatcher.registerTransport(
            transport_domain, agent_udpv4_endpoint[0])

        log.info('Listening at UDP/IPv4 endpoint %s, transport ID '
                 '%s' % (agent_udpv4_endpoint[1],
                         '.'.join([str(handler) for handler in transport_domain])))

    transport_index = args.transport_id_offset

    for agent_udpv6_endpoint in args.agent_udpv6_endpoints:
        transport_domain = udp6.domainName + (transport_index,)
        transport_index += 1

        agent_udpv6_endpoint = (
            endpoints.IPv4TransportEndpoints().add(agent_udpv6_endpoint))

        transport_dispatcher.registerTransport(
            transport_domain, agent_udpv6_endpoint[0])

        log.info('Listening at UDP/IPv6 endpoint %s, transport ID '
                 '%s' % (agent_udpv6_endpoint[1],
                         '.'.join([str(handler) for handler in transport_domain])))

    transport_dispatcher.registerRecvCbFun(commandResponderCbFun)

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
