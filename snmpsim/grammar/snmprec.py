from pysnmp.proto import rfc1902
from pyasn1.compat.octets import octs2str
from pyasn1.type import univ
from snmpsim.grammar.abstract import AbstractGrammar

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
               rfc1902.Counter64 ):
        tagMap[str(sum([ x for x in t.tagSet[0] ]))] = t

    def build(self, oid, tag, val): return '%s|%s|%s\n' % (oid, tag, val)

    def parse(self, line): return octs2str(line).strip().split('|', 2)
