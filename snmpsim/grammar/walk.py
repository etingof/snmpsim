#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
import re

from pyasn1.codec.ber import encoder
from pyasn1.compat.octets import octs2str, ints2octs
from pyasn1.type import univ
from pysnmp.proto import rfc1902

from snmpsim import error
from snmpsim.grammar import abstract


class WalkGrammar(abstract.AbstractGrammar):
    # case-insensitive keys as snmpwalk output tend to vary
    TAG_MAP = {
        'OID:': rfc1902.ObjectName,
        'INTEGER:': rfc1902.Integer,
        'STRING:': rfc1902.OctetString,
        'BITS:': rfc1902.Bits,
        'HEX-STRING:': rfc1902.OctetString,
        'GAUGE32:': rfc1902.Gauge32,
        'COUNTER32:': rfc1902.Counter32,
        'COUNTER64:': rfc1902.Counter64,
        'IPADDRESS:': rfc1902.IpAddress,
        'OPAQUE:': rfc1902.Opaque,
        'UNSIGNED32:': rfc1902.Unsigned32,  # this is not needed
        'TIMETICKS:': rfc1902.TimeTicks  # this is made up
    }

    @staticmethod
    def _integerFilter(value):
        try:
            int(value)
            return value

        except ValueError:
            # Clean enumeration values
            # .1.3.6.1.2.1.2.2.1.3.1 = INTEGER: ethernetCsmacd(6)
            match = re.match(r'.*?\((\-?[0-9]+)\)', value)
            if match:
                return match.group(1)

            # Clean values with UNIT suffix
            # .1.3.6.1.2.1.4.13.0 = INTEGER: 60 seconds
            match = re.match(r'(\-?[0-9]+)\s.+', value)
            if match:
                return match.group(1)

            return value

    # possible DISPLAY-HINTs parsing should occur here
    @staticmethod
    def _stringFilter(value):
        if not value:
            return value

        elif value[0] == value[-1] == '"':
            return value[1:-1]

        # .1.3.6.1.2.1.2.2.1.6.201752832 = STRING: 60:9c:9f:ec:a3:38
        elif re.match(r'^[0-9a-fA-F]{1,2}(\:[0-9a-fA-F]{1,2})+$', value):
            return [int(x, 16) for x in value.split(':')]

        else:
            return value

    @staticmethod
    def _opaqueFilter(value):
        if value.upper().startswith('FLOAT: '):
            return encoder.encode(univ.Real(float(value[7:])))

        else:
            return [int(y, 16) for y in value.split(' ')]

    @staticmethod
    def _bitsFilter(value):
        # rfc1902.Bits does not really initialize from sequences
        # Clean bits values
        # .1.3.6.1.2.1.17.6.1.1.1.0 = BITS: 5B 00 00 00   [[...]1 3 4 6 7
        match = re.match(r'^([0-9a-fA-F]{2}(\s+[0-9a-fA-F]{2})*)\s+\[', value)
        if match:
            return ints2octs([int(y, 16) for y in match.group(1).split(' ')])

        return ints2octs([int(y, 16) for y in value.split(' ')])

    @staticmethod
    def _hexStringFilter(value):
        # .1.3.6.1.2.1.3.1.1.2.2.1.172.30.1.30 = Hex-STRING: 00 C0 FF 43 CE 45   [...C.E]
        match = re.match(r'^([0-9a-fA-F]{2}(\s+[0-9a-fA-F]{2})*)\s+\[', value)
        if match:
            return [int(y, 16) for y in match.group(1).split(' ')]
        
        return [int(y, 16) for y in value.split(' ')]

    @staticmethod
    def _gaugeFilter(value):
        try:
            int(value)
            return value

        except ValueError:
            # Clean values with UNIT suffix
            # .1.3.6.1.2.1.4.31.1.1.47.1 = Gauge32: 10000 milli-seconds
            match = re.match(r'(\-?[0-9]+)\s.+', value)
            if match:
                return match.group(1)

            return value

    @staticmethod
    def _netAddressFilter(value):
        return '.'.join([str(int(y, 16)) for y in value.split(':')])

    @staticmethod
    def _timeTicksFilter(value):
        match = re.match(r'.*?\(([0-9]+)\)', value)
        if match:
            return match.group(1)

        return value

    def parse(self, line):

        filters = {
            'OPAQUE:': self._opaqueFilter,
            'INTEGER:': self._integerFilter,
            'STRING:': self._stringFilter,
            'BITS:': self._bitsFilter,
            'HEX-STRING:': self._hexStringFilter,
            'GAUGE32:': self._gaugeFilter,
            'Network Address:': self._netAddressFilter,
            'TIMETICKS:': self._timeTicksFilter
        }

        # drop possible 8-bits
        line = line.decode('ascii', 'ignore').encode()

        try:
            oid, value = octs2str(line).strip().split(' = ', 1)

        except Exception:
            raise error.SnmpsimError('broken record <%s>' % line)

        if oid and oid[0] == '.':
            oid = oid[1:]

        if value.startswith('Wrong Type (should be'):
            value = value[value.index(': ') + 2:]

        if value.startswith('No more variables left in this MIB View'):
            value = 'STRING: '

        try:
            tag, value = value.split(' ', 1)

        except ValueError:
            # this is implicit snmpwalk's fuzziness
            if value == '""' or value == 'STRING:':
                tag = 'STRING:'
                value = ''

            else:
                tag = 'TimeTicks:'

        if oid and tag:
            handler = filters.get(tag.upper(), lambda x: x)
            return oid, tag.upper(), handler(value.strip())

        raise error.SnmpsimError('broken record <%s>' % line)
