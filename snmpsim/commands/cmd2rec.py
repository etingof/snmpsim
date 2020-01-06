#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Snapshot Data Recorder
#
import argparse
import functools
import os
import sys
import time
import traceback

from pyasn1 import debug as pyasn1_debug
from pyasn1.type import univ
from pysnmp import debug as pysnmp_debug
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.error import PySnmpError
from pysnmp.proto import rfc1902
from pysnmp.proto import rfc1905
from pysnmp.smi import compiler
from pysnmp.smi import view
from pysnmp.smi.rfc1902 import ObjectIdentity

from snmpsim import confdir
from snmpsim import error
from snmpsim import log
from snmpsim import utils
from snmpsim import variation
from snmpsim import endpoints

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

VERSION_MAP = {
    '1': 0,
    '2c': 1,
    '3': 3
}

DESCRIPTION = ('SNMP simulation data recorder. Pull simulation data from '
               'SNMP agent')


def _parse_mib_object(arg, last=False):
    if '::' in arg:
        return ObjectIdentity(*arg.split('::', 1), last=last)

    else:
        return univ.ObjectIdentifier(arg)


def _parse_sized_string(arg, min_length=8):
    if len(arg) < min_length:
        raise argparse.ArgumentTypeError(
            'Value "%s" must be %s+ chars of length' % (arg, min_length))

    return arg


def main():
    variation_module = None

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

    v1arch_group = parser.add_argument_group('SNMPv1/v2c parameters')

    v1arch_group.add_argument(
        '--protocol-version', choices=['1', '2c'],
        default='2c', help='SNMPv1/v2c protocol version')

    v1arch_group.add_argument(
        '--community', type=str, default='public',
        help='SNMP community name')

    v3arch_group = parser.add_argument_group('SNMPv3 parameters')

    v3arch_group.add_argument(
        '--v3-user', metavar='<STRING>',
        type=functools.partial(_parse_sized_string, min_length=1),
        help='SNMPv3 USM user (security) name')

    v3arch_group.add_argument(
        '--v3-auth-key', type=_parse_sized_string,
        help='SNMPv3 USM authentication key (must be > 8 chars)')

    v3arch_group.add_argument(
        '--v3-auth-proto', choices=AUTH_PROTOCOLS,
        type=lambda x: x.upper(), default='NONE',
        help='SNMPv3 USM authentication protocol')

    v3arch_group.add_argument(
        '--v3-priv-key', type=_parse_sized_string,
        help='SNMPv3 USM privacy (encryption) key (must be > 8 chars)')

    v3arch_group.add_argument(
        '--v3-priv-proto', choices=PRIV_PROTOCOLS,
        type=lambda x: x.upper(), default='NONE',
        help='SNMPv3 USM privacy (encryption) protocol')

    v3arch_group.add_argument(
        '--v3-context-engine-id',
        type=lambda x: univ.OctetString(hexValue=x[2:]),
        help='SNMPv3 context engine ID')

    v3arch_group.add_argument(
        '--v3-context-name', type=str, default='',
        help='SNMPv3 context engine ID')

    parser.add_argument(
        '--use-getbulk', action='store_true',
        help='Use SNMP GETBULK PDU for mass SNMP managed objects retrieval')

    parser.add_argument(
        '--getbulk-repetitions', type=int, default=25,
        help='Use SNMP GETBULK PDU for mass SNMP managed objects retrieval')

    endpoint_group = parser.add_mutually_exclusive_group(required=True)

    endpoint_group.add_argument(
        '--agent-udpv4-endpoint', type=endpoints.parse_endpoint,
        metavar='<[X.X.X.X]:NNNNN>',
        help='SNMP agent UDP/IPv4 address to pull simulation data '
             'from (name:port)')

    endpoint_group.add_argument(
        '--agent-udpv6-endpoint',
        type=functools.partial(endpoints.parse_endpoint, ipv6=True),
        metavar='<[X:X:..X]:NNNNN>',
        help='SNMP agent UDP/IPv6 address to pull simulation data '
             'from ([name]:port)')

    parser.add_argument(
        '--timeout', type=int, default=3,
        help='SNMP command response timeout (in seconds)')

    parser.add_argument(
        '--retries', type=int, default=3,
        help='SNMP command retries')

    parser.add_argument(
        '--start-object', metavar='<MIB::Object|OID>', type=_parse_mib_object,
        default=univ.ObjectIdentifier('1.3.6'),
        help='Drop all simulation data records prior to this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--stop-object', metavar='<MIB::Object|OID>',
        type=functools.partial(_parse_mib_object, last=True),
        help='Drop all simulation data records after this OID specified '
             'as MIB object (MIB::Object) or OID (1.3.6.)')

    parser.add_argument(
        '--mib-source', dest='mib_sources', metavar='<URI|PATH>',
        action='append', type=str,
        default=['http://mibs.snmplabs.com/asn1/@mib@'],
        help='One or more URIs pointing to a collection of ASN.1 MIB files.'
             'Optional "@mib@" token gets replaced with desired MIB module '
             'name during MIB search.')

    parser.add_argument(
        '--destination-record-type', choices=variation.RECORD_TYPES,
        default='snmprec',
        help='Produce simulation data with record of this type')

    parser.add_argument(
        '--output-file', metavar='<FILE>', type=str,
        help='SNMP simulation data file to write records to')

    parser.add_argument(
        '--continue-on-errors', metavar='<tolerance-level>',
        type=int, default=0,
        help='Keep on pulling SNMP data even if intermittent errors occur')

    variation_group = parser.add_argument_group(
        'Simulation data variation options')

    parser.add_argument(
        '--variation-modules-dir', action='append', type=str,
        help='Search variation module by this path')

    variation_group.add_argument(
        '--variation-module', type=str,
        help='Pass gathered simulation data through this variation module')

    variation_group.add_argument(
        '--variation-module-options', type=str, default='',
        help='Variation module options')

    args = parser.parse_args()

    if args.debug:
        pysnmp_debug.setLogger(pysnmp_debug.Debug(*args.debug))

    if args.debug_asn1:
        pyasn1_debug.setLogger(pyasn1_debug.Debug(*args.debug_asn1))

    if args.output_file:
        ext = os.path.extsep
        ext += variation.RECORD_TYPES[args.destination_record_type].ext

        if not args.output_file.endswith(ext):
            args.output_file += ext

        record = variation.RECORD_TYPES[args.destination_record_type]
        args.output_file = record.open(args.output_file, 'wb')

    else:
        args.output_file = sys.stdout

        if sys.version_info >= (3, 0, 0):
            # binary mode write
            args.output_file = sys.stdout.buffer

        elif sys.platform == "win32":
            import msvcrt

            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    # Catch missing params

    if args.protocol_version == '3':
        if not args.v3_user:
            sys.stderr.write('ERROR: --v3-user is missing\r\n')
            parser.print_usage(sys.stderr)
            return 1

        if args.v3_priv_key and not args.v3_auth_key:
            sys.stderr.write('ERROR: --v3-auth-key is missing\r\n')
            parser.print_usage(sys.stderr)
            return 1

        if AUTH_PROTOCOLS[args.v3_auth_proto] == config.usmNoAuthProtocol:
            if args.v3_auth_key:
                args.v3_auth_proto = 'MD5'

        else:
            if not args.v3_auth_key:
                sys.stderr.write('ERROR: --v3-auth-key is missing\r\n')
                parser.print_usage(sys.stderr)
                return 1

        if PRIV_PROTOCOLS[args.v3_priv_proto] == config.usmNoPrivProtocol:
            if args.v3_priv_key:
                args.v3_priv_proto = 'DES'

        else:
            if not args.v3_priv_key:
                sys.stderr.write('ERROR: --v3-priv-key is missing\r\n')
                parser.print_usage(sys.stderr)
                return 1

    proc_name = os.path.basename(sys.argv[0])

    try:
        log.set_logger(proc_name, *args.logging_method, force=True)

        if args.log_level:
            log.set_level(args.log_level)

    except error.SnmpsimError as exc:
        sys.stderr.write('%s\r\n' % exc)
        parser.print_usage(sys.stderr)
        return 1

    if args.use_getbulk and args.protocol_version == '1':
        log.info('will be using GETNEXT with SNMPv1!')
        args.use_getbulk = False

    # Load variation module

    if args.variation_module:

        for variation_modules_dir in (
                args.variation_modules_dir or confdir.variation):
            log.info(
                'Scanning "%s" directory for variation '
                'modules...' % variation_modules_dir)

            if not os.path.exists(variation_modules_dir):
                log.info('Directory "%s" does not exist' % variation_modules_dir)
                continue

            mod = os.path.join(variation_modules_dir, args.variation_module + '.py')
            if not os.path.exists(mod):
                log.info('Variation module "%s" not found' % mod)
                continue

            ctx = {'path': mod, 'moduleContext': {}}

            try:
                with open(mod) as fl:
                    exec (compile(fl.read(), mod, 'exec'), ctx)

            except Exception as exc:
                log.error('Variation module "%s" execution failure: '
                          '%s' % (mod, exc))
                return 1

            variation_module = ctx
            log.info('Variation module "%s" loaded' % args.variation_module)
            break

        else:
            log.error('variation module "%s" not found' % args.variation_module)
            return 1

    # SNMP configuration

    snmp_engine = engine.SnmpEngine()

    if args.protocol_version == '3':

        if args.v3_priv_key is None and args.v3_auth_key is None:
            secLevel = 'noAuthNoPriv'

        elif args.v3_priv_key is None:
            secLevel = 'authNoPriv'

        else:
            secLevel = 'authPriv'

        config.addV3User(
            snmp_engine, args.v3_user,
            AUTH_PROTOCOLS[args.v3_auth_proto], args.v3_auth_key,
            PRIV_PROTOCOLS[args.v3_priv_proto], args.v3_priv_key)

        log.info(
            'SNMP version 3, Context EngineID: %s Context name: %s, SecurityName: %s, '
            'SecurityLevel: %s, Authentication key/protocol: %s/%s, Encryption '
            '(privacy) key/protocol: '
            '%s/%s' % (
                args.v3_context_engine_id and args.v3_context_engine_id.prettyPrint() or '<default>',
                args.v3_context_name and args.v3_context_name.prettyPrint() or '<default>', args.v3_user,
                secLevel, args.v3_auth_key is None and '<NONE>' or args.v3_auth_key,
                args.v3_auth_proto,
                args.v3_priv_key is None and '<NONE>' or args.v3_priv_key, args.v3_priv_proto))

    else:

        args.v3_user = 'agt'
        secLevel = 'noAuthNoPriv'

        config.addV1System(snmp_engine, args.v3_user, args.community)

        log.info(
            'SNMP version %s, Community name: '
            '%s' % (args.protocol_version, args.community))

    config.addTargetParams(
        snmp_engine, 'pms', args.v3_user, secLevel, VERSION_MAP[args.protocol_version])

    if args.agent_udpv6_endpoint:
        config.addSocketTransport(
            snmp_engine, udp6.domainName,
            udp6.Udp6SocketTransport().openClientMode())

        config.addTargetAddr(
            snmp_engine, 'tgt', udp6.domainName, args.agent_udpv6_endpoint, 'pms',
            args.timeout * 100, args.retries)

        log.info('Querying UDP/IPv6 agent at [%s]:%s' % args.agent_udpv6_endpoint)

    elif args.agent_udpv4_endpoint:
        config.addSocketTransport(
            snmp_engine, udp.domainName,
            udp.UdpSocketTransport().openClientMode())

        config.addTargetAddr(
            snmp_engine, 'tgt', udp.domainName, args.agent_udpv4_endpoint, 'pms',
            args.timeout * 100, args.retries)

        log.info('Querying UDP/IPv4 agent at %s:%s' % args.agent_udpv4_endpoint)

    log.info('Agent response timeout: %d secs, retries: '
             '%s' % (args.timeout, args.retries))

    if (isinstance(args.start_object, ObjectIdentity) or
            isinstance(args.stop_object, ObjectIdentity)):

        compiler.addMibCompiler(
            snmp_engine.getMibBuilder(), sources=args.mib_sources)

        mib_view_controller = view.MibViewController(
            snmp_engine.getMibBuilder())

        try:
            if isinstance(args.start_object, ObjectIdentity):
                args.start_object.resolveWithMib(mib_view_controller)

            if isinstance(args.stop_object, ObjectIdentity):
                args.stop_object.resolveWithMib(mib_view_controller)

        except PySnmpError as exc:
            sys.stderr.write('ERROR: %s\r\n' % exc)
            return 1

    # Variation module initialization

    if variation_module:
        log.info('Initializing variation module...')

        for x in ('init', 'record', 'shutdown'):
            if x not in variation_module:
                log.error('missing "%s" handler at variation module '
                          '"%s"' % (x, args.variation_module))
                return 1

        try:
            handler = variation_module['init']

            handler(snmpEngine=snmp_engine, options=args.variation_module_options,
                    mode='recording', startOID=args.start_object,
                    stopOID=args.stop_object)

        except Exception as exc:
            log.error(
                'Variation module "%s" initialization FAILED: '
                '%s' % (args.variation_module, exc))

        else:
            log.info(
                'Variation module "%s" initialization OK' % args.variation_module)

    data_file_handler = variation.RECORD_TYPES[args.destination_record_type]


    # SNMP worker

    def cbFun(snmp_engine, send_request_handle, error_indication,
              error_status, error_index, var_bind_table, cb_ctx):

        if error_indication and not cb_ctx['retries']:
            cb_ctx['errors'] += 1
            log.error('SNMP Engine error: %s' % error_indication)
            return

        # SNMPv1 response may contain noSuchName error *and* SNMPv2c exception,
        # so we ignore noSuchName error here
        if error_status and error_status != 2 or error_indication:
            log.error(
                'Remote SNMP error %s' % (
                        error_indication or error_status.prettyPrint()))

            if cb_ctx['retries']:
                try:
                    next_oid = var_bind_table[-1][0][0]

                except IndexError:
                    next_oid = cb_ctx['lastOID']

                else:
                    log.error('Failed OID: %s' % next_oid)

                # fuzzy logic of walking a broken OID
                if len(next_oid) < 4:
                    pass

                elif (args.continue_on_errors - cb_ctx['retries']) * 10 / args.continue_on_errors > 5:
                    next_oid = next_oid[:-2] + (next_oid[-2] + 1,)

                elif next_oid[-1]:
                    next_oid = next_oid[:-1] + (next_oid[-1] + 1,)

                else:
                    next_oid = next_oid[:-2] + (next_oid[-2] + 1, 0)

                cb_ctx['retries'] -= 1
                cb_ctx['lastOID'] = next_oid

                log.info(
                    'Retrying with OID %s (%s retries left)'
                    '...' % (next_oid, cb_ctx['retries']))

                # initiate another SNMP walk iteration
                if args.use_getbulk:
                    cmd_gen.sendVarBinds(
                        snmp_engine,
                        'tgt',
                        args.v3_context_engine_id, args.v3_context_name,
                        0, args.getbulk_repetitions,
                        [(next_oid, None)],
                        cbFun, cb_ctx)

                else:
                    cmd_gen.sendVarBinds(
                        snmp_engine,
                        'tgt',
                        args.v3_context_engine_id, args.v3_context_name,
                        [(next_oid, None)],
                        cbFun, cb_ctx)

            cb_ctx['errors'] += 1

            return

        if args.continue_on_errors != cb_ctx['retries']:
            cb_ctx['retries'] += 1

        if var_bind_table and var_bind_table[-1] and var_bind_table[-1][0]:
            cb_ctx['lastOID'] = var_bind_table[-1][0][0]

        stop_flag = False

        # Walk var-binds
        for var_bind_row in var_bind_table:
            for oid, value in var_bind_row:

                # EOM
                if args.stop_object and oid >= args.stop_object:
                    stop_flag = True  # stop on out of range condition

                elif (value is None or
                          value.tagSet in (rfc1905.NoSuchObject.tagSet,
                                           rfc1905.NoSuchInstance.tagSet,
                                           rfc1905.EndOfMibView.tagSet)):
                    stop_flag = True

                # remove value enumeration
                if value.tagSet == rfc1902.Integer32.tagSet:
                    value = rfc1902.Integer32(value)

                if value.tagSet == rfc1902.Unsigned32.tagSet:
                    value = rfc1902.Unsigned32(value)

                if value.tagSet == rfc1902.Bits.tagSet:
                    value = rfc1902.OctetString(value)

                # Build .snmprec record

                context = {
                    'origOid': oid,
                    'origValue': value,
                    'count': cb_ctx['count'],
                    'total': cb_ctx['total'],
                    'iteration': cb_ctx['iteration'],
                    'reqTime': cb_ctx['reqTime'],
                    'args.start_object': args.start_object,
                    'stopOID': args.stop_object,
                    'stopFlag': stop_flag,
                    'variationModule': variation_module
                }

                try:
                    line = data_file_handler.format(oid, value, **context)

                except error.MoreDataNotification as exc:
                    cb_ctx['count'] = 0
                    cb_ctx['iteration'] += 1

                    more_data_notification = exc

                    if 'period' in more_data_notification:
                        log.info(
                            '%s OIDs dumped, waiting %.2f sec(s)'
                            '...' % (cb_ctx['total'],
                                     more_data_notification['period']))

                        time.sleep(more_data_notification['period'])

                    # initiate another SNMP walk iteration
                    if args.use_getbulk:
                        cmd_gen.sendVarBinds(
                            snmp_engine,
                            'tgt',
                            args.v3_context_engine_id, args.v3_context_name,
                            0, args.getbulk_repetitions,
                            [(args.start_object, None)],
                            cbFun, cb_ctx)

                    else:
                        cmd_gen.sendVarBinds(
                            snmp_engine,
                            'tgt',
                            args.v3_context_engine_id, args.v3_context_name,
                            [(args.start_object, None)],
                            cbFun, cb_ctx)

                    stop_flag = True  # stop current iteration

                except error.NoDataNotification:
                    pass

                except error.SnmpsimError as exc:
                    log.error(exc)
                    continue

                else:
                    args.output_file.write(line)

                    cb_ctx['count'] += 1
                    cb_ctx['total'] += 1

                    if cb_ctx['count'] % 100 == 0:
                        log.info('OIDs dumped: %s/%s' % (
                            cb_ctx['iteration'], cb_ctx['count']))

        # Next request time
        cb_ctx['reqTime'] = time.time()

        # Continue walking
        return not stop_flag

    cb_ctx = {
        'total': 0,
        'count': 0,
        'errors': 0,
        'iteration': 0,
        'reqTime': time.time(),
        'retries': args.continue_on_errors,
        'lastOID': args.start_object
    }

    if args.use_getbulk:
        cmd_gen = cmdgen.BulkCommandGenerator()

        cmd_gen.sendVarBinds(
            snmp_engine,
            'tgt',
            args.v3_context_engine_id, args.v3_context_name,
            0, args.getbulk_repetitions,
            [(args.start_object, rfc1902.Null(''))],
            cbFun, cb_ctx)

    else:
        cmd_gen = cmdgen.NextCommandGenerator()

        cmd_gen.sendVarBinds(
            snmp_engine,
            'tgt',
            args.v3_context_engine_id, args.v3_context_name,
            [(args.start_object, rfc1902.Null(''))],
            cbFun, cb_ctx)

    log.info(
        'Sending initial %s request for %s (stop at %s)'
        '....' % (args.use_getbulk and 'GETBULK' or 'GETNEXT',
                  args.start_object, args.stop_object or '<end-of-mib>'))

    started = time.time()

    try:
        snmp_engine.transportDispatcher.runDispatcher()

    except KeyboardInterrupt:
        log.info('Shutting down process...')

    finally:
        if variation_module:
            log.info('Shutting down variation module '
                     '%s...' % args.variation_module)

            try:
                handler = variation_module['shutdown']

                handler(snmpEngine=snmp_engine,
                        options=args.variation_module_options,
                        mode='recording')

            except Exception as exc:
                log.error(
                    'Variation module %s shutdown FAILED: '
                    '%s' % (args.variation_module, exc))

            else:
                log.info(
                    'Variation module %s shutdown OK' % args.variation_module)

        snmp_engine.transportDispatcher.closeDispatcher()

        started = time.time() - started

        cb_ctx['total'] += cb_ctx['count']

        log.info(
            'OIDs dumped: %s, elapsed: %.2f sec, rate: %.2f OIDs/sec, errors: '
            '%d' % (cb_ctx['total'], started,
                    started and cb_ctx['count'] // started or 0,
                    cb_ctx['errors']))

        args.output_file.flush()
        args.output_file.close()

        return cb_ctx.get('errors', 0) and 1 or 0


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
