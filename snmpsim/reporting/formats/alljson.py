#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#
import json
import os
import re
import tempfile
import time
import uuid
from functools import wraps

from pyasn1.type import univ
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.entity import engine

from snmpsim import error
from snmpsim import log
from snmpsim.reporting.formats import base


def camel2snake(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def ensure_base_types(f):
    """Convert decorated function's kwargs to Python types.

    Also turn camel-cased keys into snake case.
    """
    def to_base_types(item):
        if isinstance(item, engine.SnmpEngine):
            item = item.snmpEngineID

        if isinstance(item, (univ.Integer, univ.OctetString,
                             univ.ObjectIdentifier)):
            item = item.prettyPrint()

            if item.startswith('0x'):
                item = item[2:]

            return item

        if isinstance(item, (udp.UdpTransportAddress, udp6.Udp6TransportAddress)):
            return str(item[0])

        return item

    def to_dct(dct):
        items = {}

        for k, v in dct.items():
            k = to_base_types(k)
            k = camel2snake(k)

            if isinstance(v, dict):
                v = to_dct(v)

            else:
                v = to_base_types(v)

            items[k] = v

        return items

    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **to_dct(kwargs))

    return decorated_function


class NestingDict(dict):
    """Dict with sub-dict as a defaulted value"""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)

        except KeyError:
            value = self[item] = type(self)()
            return value


class BaseJsonReporter(base.BaseReporter):
    """Common base for JSON-backed family of reporters.
    """

    REPORTING_PERIOD = 300
    REPORTING_FORMAT = ''
    REPORTING_VERSION = 1
    PRODUCER_UUID = str(uuid.uuid1())

    def __init__(self, *args):
        if not args:
            raise error.SnmpsimError(
                'Missing %s parameter(s). Expected: '
                '<method>:<reports-dir>[:dumping-period]' % self.__class__.__name__)

        self._reports_dir = os.path.join(args[0], self.REPORTING_FORMAT)

        if len(args) > 1:
            try:
                self.REPORTING_PERIOD = int(args[1])

            except Exception as exc:
                raise error.SnmpsimError(
                    'Malformed reports dumping period: %s' % args[1])

        try:
            if not os.path.exists(self._reports_dir):
                os.makedirs(self._reports_dir)

        except OSError as exc:
            raise error.SnmpsimError(
                'Failed to create reports directory %s: '
                '%s' % (self._reports_dir, exc))

        self._metrics = NestingDict()
        self._next_dump = time.time() + self.REPORTING_PERIOD

        log.debug(
            'Initialized %s metrics reporter for instance %s, metrics '
            'directory %s, dumping period is %s seconds' % (
                self.__class__.__name__, self.PRODUCER_UUID, self._reports_dir,
                self.REPORTING_PERIOD))

    def flush(self):
        """Dump accumulated metrics into a JSON file.

        Reset all counters upon success.
        """
        if not self._metrics:
            return

        now = int(time.time())

        if self._next_dump > now:
            return

        self._next_dump = now + self.REPORTING_PERIOD

        self._metrics['format'] = self.REPORTING_FORMAT
        self._metrics['version'] = self.REPORTING_VERSION
        self._metrics['producer'] = self.PRODUCER_UUID

        dump_path = os.path.join(self._reports_dir, '%s.json' % now)

        log.debug('Dumping JSON metrics to %s' % dump_path)

        try:
            json_doc = json.dumps(self._metrics, indent=2)

            with tempfile.NamedTemporaryFile(delete=False) as fl:
                fl.write(json_doc.encode('utf-8'))

            os.rename(fl.name, dump_path)

        except Exception as exc:
            log.error(
                'Failure while dumping metrics into '
                '%s: %s' % (dump_path, exc))

        self._metrics.clear()


class MinimalJsonReporter(BaseJsonReporter):
    """Collect activity metrics and dump brief report.

    Accumulates and periodically dumps activity metrics reflecting
    SNMP command responder performance.

    These counters are accumulated in memory for some time, then get
    written down as a JSON file indexed by time. Consumers are expected
    to process each of these files and are free to remove them.

    `MinimalJsonReporter` works with both SNMPv1/v2c and SNMPv3
    command responder.

    Activity metrics are arranged as a data structure like this:

    .. code-block:: python

    {
        'format': 'minimaljson',
        'version': 1,
        'producer': <UUID>,
        'first_update': '{timestamp}',
        'last_update': '{timestamp}',
        'transports': {
            'total': 0,
            'failures': 0
        },
        'agents': {
            'total': 0,
            'failures': 0
        },
        'data_files': {
            'total': 0,
            'failures': 0
        }
    }
    """

    REPORTING_FORMAT = 'minimaljson'

    def update_metrics(self, **kwargs):
        """Process activity update.

        Update internal counters based on activity update information.

        Parameters in `kwargs` serve two purposes: some are used to
        build activity scopes e.g. {transport_domain}->{snmp_engine},
        however those suffixed `*_count` are used to update corresponding
        activity counters that eventually will make their way to
        consumers.
        """

        root_metrics = self._metrics

        metrics = root_metrics

        now = int(time.time())

        if 'first_update' not in metrics:
            metrics['first_update'] = now

        metrics['last_update'] = now

        metrics = root_metrics

        try:
            metrics = metrics['transports']

            metrics['total'] = (
                    metrics.get('total', 0)
                    + kwargs.get('transport_call_count', 0))
            metrics['failures'] = (
                    metrics.get('failures', 0)
                    + kwargs.get('transport_failure_count', 0))

        except KeyError:
            pass

        metrics = root_metrics

        try:
            metrics = metrics['data_files']

            metrics['total'] = (
                    metrics.get('total', 0)
                    + kwargs.get('datafile_call_count', 0))
            metrics['failures'] = (
                    metrics.get('failures', 0)
                    + kwargs.get('datafile_failure_count', 0))

            # TODO: some data is still not coming from snmpsim v2carch core

        except KeyError:
            pass


class FullJsonReporter(BaseJsonReporter):
    """Collect activity metrics and dump detailed report.

    Accumulates and periodically dumps activity counters reflecting
    SNMP command responder performance.

    These counters are accumulated in memory for some time, then get
    written down as a JSON file indexed by time. Consumers are expected
    to process each of these files and are free to remove them.

    `FullJsonReporter` can only work within full SNMPv3 command responder.

    Activity metrics are arranged as a data structure like this:

    .. code-block:: python

    {
        'format': 'fulljson',
        'version': 1,
        'producer': <UUID>,
        'first_update': '{timestamp}',
        'last_update': '{timestamp}',
        '{transport_protocol}': {
            '{transport_endpoint}': {  # local address
                'transport_domain': '{transport_domain}',  # endpoint ID
                '{transport_address}', { # peer address
                    'packets': 0,
                    'parse_failures': 0,  # n/a
                    'auth_failures': 0,  # n/a
                    'context_failures': 0, # n/a
                    '{snmp_engine}': {
                        '{security_model}': {
                            '{security_level}': {
                                '{security_name}': {
                                    '{context_engine_id}': {
                                        '{context_name}': {
                                            '{pdu_type}': {
                                                '{data_file}': {
                                                    'pdus': 0,
                                                    'varbinds': 0,
                                                    'failures': 0,
                                                    '{variation_module}': {
                                                        'calls': 0,
                                                        'failures': 0
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Where `{token}` is replaced with a concrete value taken from request.
    """
    REPORTING_FORMAT = 'fulljson'

    @ensure_base_types
    def update_metrics(self, **kwargs):
        """Process activity update.

        Update internal counters based on activity update information.

        Parameters in `kwargs` serve two purposes: some are used to
        build activity scopes e.g. {transport_domain}->{snmp_engine},
        however those suffixed `*_count` are used to update corresponding
        activity counters that eventually will make their way to
        consumers.
        """

        metrics = self._metrics

        now = int(time.time())

        if 'first_update' not in metrics:
            metrics['first_update'] = now

        metrics['last_update'] = now

        try:
            metrics = metrics[kwargs['transport_protocol']]
            metrics = metrics['%s:%s' % kwargs['transport_endpoint']]
            metrics['transport_domain'] = kwargs['transport_domain']
            metrics = metrics[kwargs['transport_address']]
            metrics['packets'] = (
                    metrics.get('packets', 0)
                    + kwargs.get('transport_call_count', 0))

            # TODO: collect these counters
            metrics['parse_failures'] = 0
            metrics['auth_failures'] = 0
            metrics['context_failures'] = 0

            metrics = metrics[kwargs['snmp_engine']]
            metrics = metrics[kwargs['security_model']]
            metrics = metrics[kwargs['security_level']]
            metrics = metrics[kwargs['security_name']]
            metrics = metrics[kwargs['context_engine_id']]
            metrics = metrics[kwargs['pdu_type']]
            metrics = metrics[kwargs['data_file']]

            metrics['pdus'] = (
                    metrics.get('pdus', 0)
                    + kwargs.get('datafile_call_count', 0))
            metrics['failures'] = (
                    metrics.get('failures', 0)
                    + kwargs.get('datafile_failure_count', 0))
            metrics['varbinds'] = (
                    metrics.get('varbinds', 0)
                    + kwargs.get('varbind_count', 0))

            metrics = metrics['variations']
            metrics = metrics[kwargs['variation']]
            metrics['calls'] = (
                    metrics.get('pdus', 0)
                    + kwargs.get('variation_call_count', 0))
            metrics['failures'] = (
                    metrics.get('failures', 0)
                    + kwargs.get('variation_failure_count', 0))

        except KeyError:
            return
