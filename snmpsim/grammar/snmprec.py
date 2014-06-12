from string import digits, ascii_letters
from pysnmp.proto import rfc1902, rfc1905
from pyasn1.compat.octets import octs2str, str2octs, octs2ints
from pyasn1.type import univ
from snmpsim.grammar.abstract import AbstractGrammar
from snmpsim import error

class SnmprecGrammar(AbstractGrammar):
    alnums = set(octs2ints(str2octs(ascii_letters+digits)))
    tagMap = {}
    for t in ( rfc1902.Gauge32,
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
               rfc1905.EndOfMibView ):
        tagMap[str(sum([ x for x in t.tagSet[0] ]))] = t

    def build(self, oid, tag, val):
        if oid and tag:
            return str2octs('%s|%s|%s\n' % (oid, tag, val))
        raise error.SnmpsimError('empty OID/tag <%s/%s>' % (oid, tag))

    def parse(self, line):
        try:
            oid, tag, value = octs2str(line).strip().split('|', 2)
        except:
            raise error.SnmpsimError('broken record <%s>' % line)
        else:
            if oid and tag:
                return oid, tag, value
            raise error.SnmpsimError('broken record <%s>' % line)

    # helper functions

    def getTagByType(self, value):
        for tag, typ in self.tagMap.items():
            if typ.tagSet[0] == value.tagSet[0]:
                return tag
        raise Exception('error: unknown type of %s' % (value,))

    def hexifyValue(self, value):
        if value.tagSet in (univ.OctetString.tagSet,
                            rfc1902.Opaque.tagSet,
                            rfc1902.IpAddress.tagSet):
            nval = value.asNumbers()
            for x in nval:
                if x not in self.alnums:
                    return ''.join([ '%.2x' % x for x in nval ])
