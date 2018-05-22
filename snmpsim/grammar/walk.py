#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
import re
from pysnmp.proto import rfc1902
from pyasn1.type import univ
from pyasn1.codec.ber import encoder
from pyasn1.compat.octets import octs2str, ints2octs
from snmpsim.grammar import abstract
from snmpsim import error


class WalkGrammar(abstract.AbstractGrammar):
    # case-insensitive keys as snmpwalk output tend to vary
    tagMap = {
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

    def __integerFilter(value):
        try:
            int(value)
            return value
        except ValueError:
            # Clean enumeration values
            match = re.match('.*?\((\-?[0-9]+)\)', value) # .1.3.6.1.2.1.2.2.1.3.1 = INTEGER: ethernetCsmacd(6)
            if match:
                return match.groups()[0]
            # Clean values with UNIT suffix
            match = re.match('(\-?[0-9]+)\s.+', value) # .1.3.6.1.2.1.4.13.0 = INTEGER: 60 seconds
            if match:
                return match.groups()[0]
            return value

    # possible DISPLAY-HINTs parsing should occur here
    def __stringFilter(value):
        if not value:
            return value
        elif value[0] == value[-1] == '"':
            return value[1:-1]
        elif value.find(':') > 0:
            for x in value.split(':'):
                for y in x:
                    if y not in '0123456789ABCDEFabcdef':
                        return value
            return [int(x, 16) for x in value.split(':')]
        else:
            return value

    def __opaqueFilter(value):
        if value.upper().startswith('FLOAT: '):
            return encoder.encode(univ.Real(float(value[7:])))
        else:
            return [int(y, 16) for y in value.split(' ')]

    def __bitsFilter(value):
        # rfc1902.Bits does not really initialize from sequences
        return ints2octs([int(y, 16) for y in value.split(' ')])

    def __hexStringFilter(value):
        return [int(y, 16) for y in value.split(' ')]

    def __gaugeFilter(value):
        try:
            int(value)
            return value
        except ValueError:
            # Clean values with UNIT suffix
            match = re.match('(\-?[0-9]+)\s.+', value) # .1.3.6.1.2.1.4.31.1.1.47.1 = Gauge32: 10000 milli-seconds
            if match:
                return match.groups()[0]
            return value

    def __netAddressFilter(value):
        return '.'.join([str(int(y, 16)) for y in value.split(':')])

    def __timeTicksFilter(value):
        match = re.match('.*?\(([0-9]+)\)', value)
        if match:
            return match.groups()[0]
        return value

    filterMap = {
        'OPAQUE:': __opaqueFilter,
        'INTEGER:': __integerFilter,
        'STRING:': __stringFilter,
        'BITS:': __bitsFilter,
        'HEX-STRING:': __hexStringFilter,
        'GAUGE32:': __gaugeFilter,
        'Network Address:': __netAddressFilter,
        'TIMETICKS:': __timeTicksFilter
    }

    def parse(self, line):
        line = line.decode('ascii', 'ignore').encode()  # drop possible 8-bits
        try:
            oid, value = octs2str(line).strip().split(' = ', 1)
        except:
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
            return oid, tag.upper(), self.filterMap.get(tag.upper(), lambda x: x)(value.strip())
        raise error.SnmpsimError('broken record <%s>' % line)
