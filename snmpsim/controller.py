#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#

from pysnmp.proto import rfc1902
from pysnmp.smi import exval, indices
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6

from snmpsim import datafile
from snmpsim import log


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
         context_engine_id,
         context_name,
         pdu_type) = (execCtx['transportDomain'],
                      execCtx['transportAddress'],
                      execCtx['securityModel'],
                      execCtx['securityName'],
                      execCtx['securityLevel'],
                      execCtx['contextEngineId'],
                      execCtx['contextName'],
                      execCtx['pdu'].__class__.__name__)

        if isinstance(transport_address, udp.UdpTransportAddress):
            transport_protocol = 'udpv4'

        elif isinstance(transport_address, udp6.Udp6TransportAddress):
            transport_protocol = 'udpv6'

        else:
            transport_protocol = 'unknown'

        log.info(
            'SNMP EngineID %s, transportDomain %s, transportAddress %s, '
            'securityModel %s, securityName %s, securityLevel '
            '%s' % (hasattr(snmp_engine, 'snmpEngineID') and
                    snmp_engine.snmpEngineID.prettyPrint() or '<unknown>',
                    transport_domain, transport_address, security_model,
                    security_name, security_level))

        return {'snmpEngine': snmp_engine,
                'transportDomain': rfc1902.ObjectIdentifier(transport_domain),
                'transportAddress': transport_address,
                'transportEndpoint': transport_address.getLocalAddress(),
                'transportProtocol': transport_protocol,
                'securityModel': security_model,
                'securityName': security_name,
                'securityLevel': security_level,
                'contextEngineId': context_engine_id,
                'contextName': context_name,
                'pduType': pdu_type,
                'nextFlag': next_flag,
                'setFlag': set_flag}

    def readVars(self, var_binds, acInfo=None):
        return self._data_file.process_var_binds(
            var_binds, **self._get_call_context(acInfo, False))

    def readNextVars(self, var_binds, acInfo=None):
        return self._data_file.process_var_binds(
            var_binds, **self._get_call_context(acInfo, True))

    def writeVars(self, var_binds, acInfo=None):
        return self._data_file.process_var_binds(
            var_binds, **self._get_call_context(acInfo, False, True))


class DataIndexInstrumController(object):
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


MIB_CONTROLLERS = {
    datafile.DataFile.layout: MibInstrumController
}

