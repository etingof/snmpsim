from pysnmp.proto import rfc1902, rfc1905
from pyasn1.compat.octets import octs2str, str2octs
from pyasn1.type import univ
from snmpsim.grammar.abstract import AbstractGrammar
from snmpsim import error

class SnmprecGrammar(AbstractGrammar):
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

    def build(self, oid, tag, val): return str2octs('%s|%s|%s\n' % (oid, tag, val))

    def parse(self, line):
        try:
            oid, tag, value = octs2str(line).strip().split('|', 2)
        except:
            raise error.SnmpsimError('broken record <%s>' % line)
        else:
            return oid, tag, value

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
            if nval and nval[-1] == 32 or \
                    [ x for x in nval if x < 32 or x > 126 ]:
                return ''.join([ '%.2x' % x for x in nval ])
