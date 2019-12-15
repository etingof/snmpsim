#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from string import ascii_letters
from string import digits

from pyasn1.compat.octets import octs2str, str2octs, octs2ints
from pyasn1.type import univ
from pysnmp.proto import rfc1902, rfc1905

from snmpsim import error
from snmpsim.grammar.abstract import AbstractGrammar


class SnmprecGrammar(AbstractGrammar):

    ALNUMS = set(octs2ints(str2octs(ascii_letters + digits)))

    TAG_MAP = {}

    SNMP_TYPES = (
        rfc1902.Gauge32,
        rfc1902.Integer32,
        rfc1902.IpAddress,
        univ.Null,
        univ.ObjectIdentifier,
        rfc1902.OctetString,
        rfc1902.TimeTicks,
        rfc1902.Opaque,
        rfc1902.Counter32,
        rfc1902.Counter64,
        rfc1905.NoSuchObject,
        rfc1905.NoSuchInstance,
        rfc1905.EndOfMibView
    )

    for typ in SNMP_TYPES:
        TAG_MAP[str(sum([x for x in typ.tagSet[0]]))] = typ

    def build(self, oid, tag, val):
        if oid and tag:
            return str2octs('%s|%s|%s\n' % (oid, tag, val))

        raise error.SnmpsimError('empty OID/tag <%s/%s>' % (oid, tag))

    def parse(self, line):
        try:
            oid, tag, value = octs2str(line).strip().split('|', 2)

        except Exception as exc:
            raise error.SnmpsimError(
                'broken record <%s>: %s' % (line, exc))

        else:
            if oid and tag:
                return oid, tag, value

            raise error.SnmpsimError('broken record <%s>' % line)

    # helper functions

    def get_tag_by_type(self, value):
        for tag, typ in self.TAG_MAP.items():
            if typ.tagSet[0] == value.tagSet[0]:
                return tag

        raise Exception('error: unknown type of %s' % (value,))

    def hexify_value(self, value):
        if value.tagSet in (univ.OctetString.tagSet,
                            rfc1902.Opaque.tagSet,
                            rfc1902.IpAddress.tagSet):

            nval = value.asNumbers()

            for x in nval:
                if (value.tagSet == rfc1902.IpAddress.tagSet or
                            x not in self.ALNUMS):
                    return ''.join(['%.2x' % x for x in nval])
