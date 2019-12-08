#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from pyasn1.compat.octets import octs2str
from pyasn1.type import univ
from pysnmp.proto import rfc1902

from snmpsim import error
from snmpsim.grammar import abstract


class SapGrammar(abstract.AbstractGrammar):

    TAG_MAP = {
        'Counter': rfc1902.Counter32,
        'Gauge': rfc1902.Gauge32,
        'Integer': rfc1902.Integer32,
        'IpAddress': rfc1902.IpAddress,
        #        '<not implemented?>': univ.Null,
        'ObjectID': univ.ObjectIdentifier,
        'OctetString': rfc1902.OctetString,
        'TimeTicks': rfc1902.TimeTicks,
        'Counter64': rfc1902.Counter64
    }

    @staticmethod
    def _stringFilter(value):
        if value[:2] == '0x':
            value = [int(value[x:x + 2], 16)
                     for x in range(2, len(value[2:]) + 2, 2)]

        return value

    def parse(self, line):

        filters = {
            'OctetString': self._stringFilter
        }

        try:
            oid, tag, value = [x.strip() for x in octs2str(line).split(',', 2)]

        except Exception as exc:
            raise error.SnmpsimError(
                'broken record <%s>: %s' % (line, exc))

        else:
            if oid and tag:
                handler = filters.get(tag, lambda x: x)
                return oid, tag, handler(value.strip())

            raise error.SnmpsimError('broken record <%s>' % line)
