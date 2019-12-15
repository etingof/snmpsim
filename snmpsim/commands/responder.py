#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#
import argparse
import os
import stat
import sys
import traceback
from hashlib import md5

from pyasn1 import debug as pyasn1_debug
from pyasn1.codec.ber import decoder
from pyasn1.codec.ber import encoder
from pyasn1.compat.octets import null
from pyasn1.compat.octets import str2octs
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pysnmp import debug as pysnmp_debug
from pysnmp import error
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.carrier.asyncore.dgram import unix
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.entity import config
from pysnmp.entity import engine
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.entity.rfc3413 import context
from pysnmp.proto import api
from pysnmp.proto import rfc1902
from pysnmp.proto import rfc1905
from pysnmp.smi import exval, indices
from pysnmp.smi.error import MibOperationError

from snmpsim import confdir
from snmpsim import daemon
from snmpsim import log
from snmpsim import utils
from snmpsim.error import NoDataNotification
from snmpsim.error import SnmpsimError
from snmpsim.record import dump
from snmpsim.record import mvc
from snmpsim.record import sap
from snmpsim.record import snmprec
from snmpsim.record import walk
from snmpsim.record.search.database import RecordIndex
from snmpsim.record.search.file import get_record
from snmpsim.record.search.file import search_record_by_oid

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

RECORD_TYPES = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
}

# Poor man's v2c->v1 translation
SNMP_ERROR_MAP = {
    rfc1902.Counter64.tagSet: 5,
    rfc1905.NoSuchObject.tagSet: 2,
    rfc1905.NoSuchInstance.tagSet: 2,
    rfc1905.EndOfMibView.tagSet: 2
}

SELF_LABEL = 'self'

DESCRIPTION = (
    'SNMP agent simulator: responds to SNMP requests, variate responses '
    'based on transport addresses, SNMP community name, SNMPv3 context '
    'or via variation modules.')


class TransportEndpointsBase:
    def __init__(self):
        self.__endpoint = None

    def add(self, addr):
        self.__endpoint = self._addEndpoint(addr)
        return self

    def _addEndpoint(self, addr):
        raise NotImplementedError()

    def __len__(self):
        return len(self.__endpoint)

    def __getitem__(self, i):
        return self.__endpoint[i]


class IPv4TransportEndpoints(TransportEndpointsBase):
    def _addEndpoint(self, addr):
        f = lambda h, p=161: (h, int(p))

        try:
            h, p = f(*addr.split(':'))

        except Exception:
            raise SnmpsimError('improper IPv4/UDP endpoint %s' % addr)

        return udp.UdpTransport().openServerMode((h, p)), addr


class IPv6TransportEndpoints(TransportEndpointsBase):
    def _addEndpoint(self, addr):
        if not udp6:
            raise SnmpsimError('This system does not support UDP/IP6')

        if addr.find(']:') != -1 and addr[0] == '[':
            h, p = addr.split(']:')

            try:
                h, p = h[1:], int(p)

            except Exception:
                raise SnmpsimError('improper IPv6/UDP endpoint %s' % addr)

        elif addr[0] == '[' and addr[-1] == ']':
            h, p = addr[1:-1], 161

        else:
            h, p = addr, 161

        return udp6.Udp6Transport().openServerMode((h, p)), addr


# Extended snmprec record handler

class SnmprecRecordMixIn(object):

    def evaluateValue(self, oid, tag, value, **context):
        # Variation module reference
        if ':' in tag:
            mod_name, tag = tag[tag.index(':')+1:], tag[:tag.index(':')]

        else:
            mod_name = None

        if mod_name:
            if ('variationModules' in context and
                    mod_name in context['variationModules']):

                if 'dataValidation' in context:
                    return oid, tag, univ.Null

                else:
                    if context['setFlag']:

                        hexvalue = self.grammar.hexify_value(
                            context['origValue'])

                        if hexvalue is not None:
                            context['hexvalue'] = hexvalue
                            context['hextag'] = self.grammar.get_tag_by_type(
                                context['origValue'])
                            context['hextag'] += 'x'

                    # prepare agent and record contexts on first reference
                    (variation_module,
                     agent_contexts,
                     record_contexts) = context['variationModules'][mod_name]

                    if context['dataFile'] not in agent_contexts:
                        agent_contexts[context['dataFile']] = {}

                    if context['dataFile'] not in record_contexts:
                        record_contexts[context['dataFile']] = {}

                    variation_module['agentContext'] = agent_contexts[context['dataFile']]

                    record_contexts = record_contexts[context['dataFile']]

                    if oid not in record_contexts:
                        record_contexts[oid] = {}

                    variation_module['recordContext'] = record_contexts[oid]

                    handler = variation_module['variate']

                    # invoke variation module
                    oid, tag, value = handler(oid, tag, value, **context)

            else:
                raise SnmpsimError(
                    'Variation module "%s" referenced but not '
                    'loaded\r\n' % mod_name)

        if not mod_name:
            if 'dataValidation' in context:
                snmprec.SnmprecRecord.evaluate_value(
                    self, oid, tag, value, **context)

            if (not context['nextFlag'] and
                    not context['exactMatch'] or context['setFlag']):
                return context['origOid'], tag, context['errorStatus']

        if not hasattr(value, 'tagSet'):  # not already a pyasn1 object
            return snmprec.SnmprecRecord.evaluate_value(
                       self, oid, tag, value, **context)

        return oid, tag, value

    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)

        oid = self.evaluate_oid(oid)

        if context.get('oidOnly'):
            value = None

        else:
            try:
                oid, tag, value = self.evaluateValue(oid, tag, value, **context)

            except NoDataNotification:
                raise

            except MibOperationError:
                raise

            except PyAsn1Error as exc:
                raise SnmpsimError(
                    'value evaluation for %s = %r failed: '
                    '%s\r\n' % (oid, value, exc))

        return oid, value


class SnmprecRecord(SnmprecRecordMixIn, snmprec.SnmprecRecord):
    pass


RECORD_TYPES[SnmprecRecord.ext] = SnmprecRecord()


class CompressedSnmprecRecord(
        SnmprecRecordMixIn, snmprec.CompressedSnmprecRecord):
    pass


RECORD_TYPES[CompressedSnmprecRecord.ext] = CompressedSnmprecRecord()


class AbstractLayout:
    layout = '?'


class DataFile(AbstractLayout):
    layout = 'text'
    opened_queue = []
    max_queue_entries = 31  # max number of open text and index files

    def __init__(self, textFile, textParser, variationModules):
        self._record_index = RecordIndex(textFile, textParser)
        self._text_parser = textParser
        self._text_file = os.path.abspath(textFile)
        self._variation_modules = variationModules
        
    def indexText(self, forceIndexBuild=False, validateData=False):
        self._record_index.create(forceIndexBuild, validateData)
        return self

    def close(self):
        self._record_index.close()
    
    def getHandles(self):
        if not self._record_index.is_open():
            if len(DataFile.opened_queue) > self.max_queue_entries:
                log.info('Closing %s' % self)
                DataFile.opened_queue[0].close()
                del DataFile.opened_queue[0]

            DataFile.opened_queue.append(self)

            log.info('Opening %s' % self)

        return self._record_index.get_handles()

    def processVarBinds(self, var_binds, **context):
        rsp_var_binds = []

        if context.get('nextFlag'):
            error_status = exval.endOfMib

        else:
            error_status = exval.noSuchInstance

        try:
            text, db = self.getHandles()

        except SnmpsimError as exc:
            log.error(
                'Problem with data file or its index: %s' % exc)

            return [(vb[0], error_status) for vb in var_binds]

        vars_remaining = vars_total = len(var_binds)

        log.info(
            'Request var-binds: %s, flags: %s, '
            '%s' % (', '.join(['%s=<%s>' % (vb[0], vb[1].prettyPrint())
                               for vb in var_binds]),
                    context.get('nextFlag') and 'NEXT' or 'EXACT',
                    context.get('setFlag') and 'SET' or 'GET'))

        for oid, val in var_binds:
            text_oid = str(univ.OctetString('.'.join(['%s' % x for x in oid])))

            try:
                line = self._record_index.lookup(
                    str(univ.OctetString('.'.join(['%s' % x for x in oid]))))

            except KeyError:
                offset = search_record_by_oid(oid, text, self._text_parser)
                subtree_flag = exact_match = False

            else:
                offset, subtree_flag, prev_offset = line.split(str2octs(','), 2)
                subtree_flag, exact_match = int(subtree_flag), True

            offset = int(offset)

            text.seek(offset)

            vars_remaining -= 1

            line, _, _ = get_record(text)  # matched line
 
            while True:
                if exact_match:
                    if context.get('nextFlag') and not subtree_flag:

                        _next_line, _, _ = get_record(text)  # next line

                        if _next_line:
                            _next_oid, _ = self._text_parser.evaluate(
                                _next_line, oidOnly=True)

                            try:
                                _, subtree_flag, _ = self._record_index.lookup(
                                    str(_next_oid)).split(str2octs(','), 2)

                            except KeyError:
                                log.error(
                                    'data error for %s at %s, index '
                                    'broken?' % (self, _next_oid))
                                line = ''  # fatal error

                            else:
                                subtree_flag = int(subtree_flag)
                                line = _next_line

                        else:
                            line = _next_line

                else:  # search function above always rounds up to the next OID
                    if line:
                        _oid, _ = self._text_parser.evaluate(
                            line, oidOnly=True
                        )

                    else:  # eom
                        _oid = 'last'

                    try:
                        _, _, _prev_offset = self._record_index.lookup(
                            str(_oid)).split(str2octs(','), 2)

                    except KeyError:
                        log.error(
                            'data error for %s at %s, index '
                            'broken?' % (self, _oid))
                        line = ''  # fatal error

                    else:
                        _prev_offset = int(_prev_offset)

                        # previous line serves a subtree?
                        if _prev_offset >= 0:
                            text.seek(_prev_offset)
                            _prev_line, _, _ = get_record(text)
                            _prev_oid, _ = self._text_parser.evaluate(
                                _prev_line, oidOnly=True)

                            if _prev_oid.isPrefixOf(oid):
                                # use previous line to the matched one
                                line = _prev_line
                                subtree_flag = True

                if not line:
                    _oid = oid
                    _val = error_status
                    break

                call_context = context.copy()
                call_context.update(
                    (),
                    origOid=oid, 
                    origValue=val,
                    dataFile=self._text_file,
                    subtreeFlag=subtree_flag,
                    exactMatch=exact_match,
                    errorStatus=error_status,
                    varsTotal=vars_total,
                    varsRemaining=vars_remaining,
                    variationModules=self._variation_modules
                )
 
                try:
                    _oid, _val = self._text_parser.evaluate(
                        line, **call_context)

                    if _val is exval.endOfMib:
                        exact_match = True
                        subtree_flag = False
                        continue

                except NoDataNotification:
                    raise

                except MibOperationError:
                    raise

                except Exception as exc:
                    _oid = oid
                    _val = error_status
                    log.error(
                        'data error at %s for %s: %s' % (self, text_oid, exc))

                break

            rsp_var_binds.append((_oid, _val))

        log.info(
            'Response var-binds: %s' % (
                ', '.join(['%s=<%s>' % (
                    vb[0], vb[1].prettyPrint()) for vb in rsp_var_binds])))

        return rsp_var_binds
 
    def __str__(self):
        return '%s controller' % self._text_file


def get_data_files(tgt_dir, top_len=None):
    if top_len is None:
        top_len = len(tgt_dir.split(os.path.sep))

    dir_content = []

    for d_file in os.listdir(tgt_dir):
        full_path = os.path.join(tgt_dir, d_file)

        inode = os.lstat(full_path)

        if stat.S_ISLNK(inode.st_mode):
            rel_path = full_path.split(os.path.sep)[top_len:]
            full_path = os.readlink(full_path)

            if not os.path.isabs(full_path):
                full_path = os.path.join(tgt_dir, full_path)

            inode = os.stat(full_path)

        else:
            rel_path = full_path.split(os.path.sep)[top_len:]

        if stat.S_ISDIR(inode.st_mode):
            dir_content += get_data_files(full_path, top_len)
            continue

        if not stat.S_ISREG(inode.st_mode):
            continue

        for dExt in RECORD_TYPES:
            if d_file.endswith(dExt):
                break

        else:
            continue

        # just the file name would serve for agent identification
        if rel_path[0] == SELF_LABEL:
            rel_path = rel_path[1:]

        if len(rel_path) == 1 and rel_path[0] == SELF_LABEL + os.path.extsep + dExt:
            rel_path[0] = rel_path[0][4:]

        ident = os.path.join(*rel_path)
        ident = ident[:-len(dExt) - 1]
        ident = ident.replace(os.path.sep, '/')

        dir_content.append(
            (full_path,
             RECORD_TYPES[dExt],
             ident)
        )

    return dir_content


class MibInstrumController(object):
    """Lightweight MIB instrumentation (API-compatible with pysnmp's)"""
    def __init__(self, data_file):
        self._data_file = data_file

    def __str__(self):
        return str(self._data_file)

    def _get_call_context(self, ac_info, next_flag=False, set_flag=False):
        if ac_info is None:
            return {'nextFlag': next_flag,
                    'setFlag': set_flag}

        ac_fun, snmp_engine = ac_info  # we injected snmpEngine object earlier

        # this API is first introduced in pysnmp 4.2.6
        execCtx = snmp_engine.observer.getExecutionContext(
                'rfc3412.receiveMessage:request')

        (transport_domain,
         transport_address,
         security_model,
         security_name,
         security_level,
         context_name,
         pdu_type) = (execCtx['transportDomain'],
                      execCtx['transportAddress'],
                      execCtx['securityModel'],
                      execCtx['securityName'],
                      execCtx['securityLevel'],
                      execCtx['contextName'],
                      execCtx['pdu'].getTagSet())

        log.info(
            'SNMP EngineID %s, transportDomain %s, transportAddress %s, '
            'securityModel %s, securityName %s, securityLevel '
            '%s' % (hasattr(snmp_engine, 'snmpEngineID') and
                    snmp_engine.snmpEngineID.prettyPrint() or '<unknown>',
                    transport_domain, transport_address, security_model,
                    security_name, security_level))

        return {'snmpEngine': snmp_engine,
                'transportDomain': transport_domain,
                'transportAddress': transport_address,
                'securityModel': security_model,
                'securityName': security_name,
                'securityLevel': security_level,
                'contextName': context_name,
                'nextFlag': next_flag,
                'setFlag': set_flag}

    def readVars(self, var_binds, acInfo=None):
        return self._data_file.processVarBinds(
                var_binds, **self._get_call_context(acInfo, False))

    def readNextVars(self, var_binds, acInfo=None):
        return self._data_file.processVarBinds(
                var_binds, **self._get_call_context(acInfo, True))

    def writeVars(self, var_binds, acInfo=None):
        return self._data_file.processVarBinds(
                var_binds, **self._get_call_context(acInfo, False, True))


class DataIndexInstrumController:
    """Data files index as a MIB instrumentation in a dedicated SNMP context"""

    index_sub_oid = (1,)

    def __init__(self, base_oid=(1, 3, 6, 1, 4, 1, 20408, 999)):
        self._db = indices.OidOrderedDict()
        self._index_oid = base_oid + self.index_sub_oid
        self._idx = 1

    def __str__(self):
        return '<index> controller'

    def readVars(self, var_binds, acInfo=None):
        return [(vb[0], self._db.get(vb[0], exval.noSuchInstance))
                for vb in var_binds]

    def _get_next_val(self, key, default):
        try:
            key = self._db.nextKey(key)

        except KeyError:
            return key, default

        else:
            return key, self._db[key]
                                                            
    def readNextVars(self, var_binds, acInfo=None):
        return [self._get_next_val(vb[0], exval.endOfMib)
                for vb in var_binds]

    def writeVars(self, var_binds, acInfo=None):
        return [(vb[0], exval.noSuchInstance)
                for vb in var_binds]
    
    def add_data_file(self, *args):
        for idx in range(len(args)):
            self._db[
                self._index_oid + (idx + 1, self._idx)
                ] = rfc1902.OctetString(args[idx])
        self._idx += 1


mib_instrum_controller_set = {
    DataFile.layout: MibInstrumController
}


# Suggest variations of context name based on request data
def probe_context(transport_domain, transport_address,
                  context_engine_id, context_name):
    if context_engine_id:
        candidate = [
            context_engine_id, context_name, '.'.join(
                [str(x) for x in transport_domain])]

    else:
        # try legacy layout w/o contextEnginId in the path
        candidate = [
            context_name, '.'.join(
                [str(x) for x in transport_domain])]

    if transport_domain[:len(udp.domainName)] == udp.domainName:
        candidate.append(transport_address[0])

    elif udp6 and transport_domain[:len(udp6.domainName)] == udp6.domainName:
        candidate.append(str(transport_address[0]).replace(':', '_'))

    elif unix and transport_domain[:len(unix.domainName)] == unix.domainName:
        candidate.append(transport_address)

    candidate = [str(x) for x in candidate if x]

    while candidate:
        yield rfc1902.OctetString(
            os.path.normpath(
                os.path.sep.join(candidate)).replace(os.path.sep, '/')).asOctets()
        del candidate[-1]

    # try legacy layout w/o contextEnginId in the path
    if context_engine_id:
        for candidate in probe_context(
                transport_domain, transport_address, None, context_name):
            yield candidate


def probe_hash_context(self, snmp_engine):
    """v3arch SNMP context name searcher"""
    # this API is first introduced in pysnmp 4.2.6
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
        context_engine_id = SELF_LABEL

    else:
        context_engine_id = context_engine_id.prettyPrint()

    for candidate in probe_context(
            transport_domain, transport_address,
            context_engine_id, context_name):

        if len(candidate) > 32:
            probed_context_name = md5(candidate).hexdigest()

        else:
            probed_context_name = candidate

        try:
            mib_instrum = self.snmpContext.getMibInstrum(probed_context_name)

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
        mib_instrum = self.snmpContext.getMibInstrum(context_name)
        log.info(
            'Using %s selected by contextName "%s", transport ID %s, '
            'source address %s' % (mib_instrum, context_name,
                                   univ.ObjectIdentifier(transport_domain),
                                   transport_address[0]))

    if not isinstance(mib_instrum, (MibInstrumController, DataIndexInstrumController)):
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


def main():

    variation_modules_options = {}
    variation_modules = {}

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
        help='SNMP simulation data file to write records to')

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

    args, unparsed_args = parser.parse_known_args()

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
            'ERROR: Unmatched command-line parameter %s\r\n' % name)
        parser.print_usage(sys.stderr)
        return 1

    if args.cache_dir:
        confdir.cache = args.cache_dir

    if args.variation_modules_dir:
        confdir.variation = args.variation_modules_dir

    for option in args.variation_module_options:
        args = option.split(':', 1)

        try:
            mod_name, args = args[0], args[1]

        except Exception as exc:
            sys.stderr.write(
                'ERROR: improper variation module options: %s\r\n')
            parser.print_usage(sys.stderr)
            return 1

        if '=' in mod_name:
            mod_name, alias = mod_name.split('=', 1)

        else:
            alias = os.path.splitext(os.path.basename(mod_name))[0]

        if mod_name not in variation_modules_options:
            variation_modules_options[mod_name] = []

        variation_modules_options[mod_name].append((alias, args))

        if args.args_from_file:
            try:
                with open(args.args_from_file) as fl:
                    snmp_args.extend([x.split('=', 1) for x in fl.read().split()])

            except Exception as exc:
                sys.stderr.write(
                    'ERROR: file %s opening failure: '
                    '%s\r\n' % (args.args_from_file, exc))
                parser.print_usage(sys.stderr)
                return 1

    with daemon.PrivilegesOf(args.process_user, args.process_group):

        try:
            log.setLogger(__name__, *args.logging_method, force=True)

            if args.log_level:
                log.setLevel(args.log_level)

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

    if args.v2c_arch and (
            args.v3_only or any(x for x in snmp_args
                                if x[0].startswith('--v3'))):
        sys.stderr.write(
            'ERROR: either of --v2c-arch or --v3-* options should be used\r\n')
        parser.print_usage(sys.stderr)
        return 1

    # hook up variation modules

    for variation_modules_dir in confdir.variation:
        log.info(
            'Scanning "%s" directory for variation '
            'modules...' % variation_modules_dir)

        if not os.path.exists(variation_modules_dir):
            log.info('Directory "%s" does not exist' % variation_modules_dir)
            continue

        for d_file in os.listdir(variation_modules_dir):
            if d_file[-3:] != '.py':
                continue

            _to_load = []

            mod_name = os.path.splitext(os.path.basename(d_file))[0]

            if mod_name in variation_modules_options:
                while variation_modules_options[mod_name]:
                    alias, params = variation_modules_options[mod_name].pop()
                    _to_load.append((alias, params))

                del variation_modules_options[mod_name]

            else:
                _to_load.append((mod_name, ''))

            mod = os.path.abspath(os.path.join(variation_modules_dir, d_file))

            for alias, params in _to_load:
                if alias in variation_modules:
                    log.error(
                        'ignoring duplicate variation module "%s" at '
                        '"%s"' % (alias, mod))
                    continue

                ctx = {
                    'path': mod,
                    'alias': alias,
                    'args': params,
                    'moduleContext': {}
                }

                try:
                    with open(mod) as fl:
                        exec(compile(fl.read(), mod, 'exec'), ctx)

                except Exception as exc:
                    log.error(
                        'Variation module "%s" execution failure: '
                        '%s' % (mod, exc))
                    return 1

                # moduleContext, agentContexts, recordContexts
                variation_modules[alias] = ctx, {}, {}

        log.info('A total of %s modules found in '
                 '%s' % (len(variation_modules), variation_modules_dir))

    if variation_modules_options:
        log.msg('WARNING: unused options for variation modules: '
                '%s' % ', '.join(variation_modules_options))

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

    if variation_modules:
        log.info('Initializing variation modules...')

        for name, modules_contexts in variation_modules.items():

            body = modules_contexts[0]

            for x in ('init', 'variate', 'shutdown'):
                if x not in body:
                    log.error('missing "%s" handler at variation module '
                              '"%s"' % (x, name))
                    return 1

            try:
                with daemon.PrivilegesOf(args.process_user, args.process_group):
                    body['init'](options=body['args'], mode='variating')

            except Exception as exc:
                log.error(
                    'Variation module "%s" from "%s" load FAILED: '
                    '%s' % (body['alias'], body['path'], exc))

            else:
                log.info(
                    'Variation module "%s" from "%s" '
                    'loaded OK' % (body['alias'], body['path']))

    # Bind transport endpoints
    for idx, opt in enumerate(snmp_args):
        if opt[0] == '--agent-udpv4-endpoint':
            snmp_args[idx] = (opt[0], IPv4TransportEndpoints().add(opt[1]))

        elif opt[0] == '--agent-udpv6-endpoint':
            snmp_args[idx] = (opt[0], IPv6TransportEndpoints().add(opt[1]))

    def configure_managed_objects(
            data_dirs, data_index_instrum_controller, snmp_engine=None,
            snmp_context=None):
        """Build pysnmp Managed Objects base from data files information"""

        _mib_instrums = {}
        _data_files = {}

        for dataDir in data_dirs:

            log.info(
                'Scanning "%s" directory for %s data '
                'files...' % (dataDir, ','.join([' *%s%s' % (os.path.extsep, x.ext)
                                                 for x in RECORD_TYPES.values()])))

            if not os.path.exists(dataDir):
                log.info('Directory "%s" does not exist' % dataDir)
                continue

            log.msg.inc_ident()

            for full_path, text_parser, community_name in get_data_files(dataDir):
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
                    data_file = DataFile(full_path, text_parser, variation_modules)
                    data_file.indexText(args.force_index_rebuild, args.validate_data)

                    mib_instrum = mib_instrum_controller_set[data_file.layout](data_file)

                    _mib_instrums[full_path] = mib_instrum
                    _data_files[community_name] = full_path

                    log.info('Configuring %s' % (mib_instrum,))

                log.info('SNMPv1/2c community name: %s' % (community_name,))

                if args.v2c_arch:
                    contexts[univ.OctetString(community_name)] = mib_instrum

                    data_index_instrum_controller.add_data_file(
                        full_path, community_name
                    )

                else:
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

    # Start configuring SNMP engine(s)

    transport_dispatcher = AsyncoreDispatcher()

    if args.v2c_arch:

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

                for candidate in probe_context(transport_domain, transport_address,
                                               context_engine_id=SELF_LABEL,
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

                        if val.tagSet in SNMP_ERROR_MAP:
                            var_binds = p_mod.apiPDU.getVarBinds(req_pdu)

                            p_mod.apiPDU.setErrorStatus(
                                rsp_pdu, SNMP_ERROR_MAP[val.tagSet])
                            p_mod.apiPDU.setErrorIndex(
                                rsp_pdu, idx + 1)

                            break

                p_mod.apiPDU.setVarBinds(rsp_pdu, var_binds)

                transport_dispatcher.sendMessage(
                    encoder.encode(rsp_msg), transport_domain, transport_address)

            return whole_msg

        # Configure access to data index

        agent_udpv4_endpoints = []
        agent_udpv6_endpoints = []
        data_dirs = []

        for opt in snmp_args:
            if opt[0] == '--data-dir':
                data_dirs.append(opt[1])

            if opt[0] == '--agent-udpv4-endpoint':
                agent_udpv4_endpoints.append(opt[1])

            elif opt[0] == '--agent-udpv6-endpoint':
                agent_udpv6_endpoints.append(opt[1])

        if not agent_udpv4_endpoints and not agent_udpv6_endpoints:
            log.error('agent endpoint address(es) not specified')
            return 1

        log.info('Maximum number of variable bindings in SNMP '
                 'response: %s' % args.max_var_binds)

        data_index_instrum_controller = DataIndexInstrumController()

        contexts = {univ.OctetString('index'): data_index_instrum_controller}

        with daemon.PrivilegesOf(args.process_user, args.process_group):
            configure_managed_objects(
                data_dirs or confdir.data, data_index_instrum_controller)

        contexts['index'] = data_index_instrum_controller

        # Configure socket server

        transport_index = args.transport_id_offset
        for agent_udpv4_endpoint in agent_udpv4_endpoints:
            transport_domain = udp.domainName + (transport_index,)
            transport_index += 1

            transport_dispatcher.registerTransport(
                transport_domain, agent_udpv4_endpoint[0])

            log.info('Listening at UDP/IPv4 endpoint %s, transport ID '
                     '%s' % (agent_udpv4_endpoint[1],
                             '.'.join([str(x) for x in transport_domain])))

        transport_index = args.transport_id_offset

        for agent_udpv6_endpoint in agent_udpv6_endpoints:
            transport_domain = udp6.domainName + (transport_index,)
            transport_index += 1

            transport_dispatcher.registerTransport(
                    transport_domain, agent_udpv6_endpoint[0])

            log.info('Listening at UDP/IPv6 endpoint %s, transport ID '
                     '%s' % (agent_udpv6_endpoint[1],
                             '.'.join([str(x) for x in transport_domain])))

        transport_dispatcher.registerRecvCbFun(commandResponderCbFun)

    else:  # v3 arch

        transport_dispatcher.registerRoutingCbFun(lambda td, t, d: td)

        if snmp_args and snmp_args[0][0] != '--v3-engine-id':
            snmp_args.insert(0, ('--v3-engine-id', 'auto'))

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

                    log.info('--- Data directories configuration')

                    for v3_context_engine_id, ctx_data_dirs in v3_context_engine_ids:
                        snmp_context = context.SnmpContext(snmp_engine, v3_context_engine_id)
                        # unregister default context
                        snmp_context.unregisterContextName(null)

                        log.msg(
                            'SNMPv3 Context Engine ID: '
                            '%s' % snmp_context.contextEngineId.prettyPrint())

                        data_index_instrum_controller = DataIndexInstrumController()

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
                                    '.'.join([str(x) for x in transport_domain])))

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
                                    '.'.join([str(x) for x in transport_domain])))

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
                    if v3_engine_id.lower() == 'auto':
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
