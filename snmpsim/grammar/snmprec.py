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

    def build(self, oid, val):
        output = '%s|%s' % (
            oid.prettyPrint(), sum([ x for x in val.tagSet[0] ])
        )
        if val.tagSet in (univ.OctetString.tagSet,
                          rfc1902.Opaque.tagSet,
                          rfc1902.IpAddress.tagSet):
            nval = val.asNumbers()
            if nval and nval[-1] == 32 or \
                     [ x for x in nval if x < 32 or x > 126 ]:
                output += 'x'
                val = ''.join([ '%.2x' % x for x in nval ])
        else:
            val = val.prettyPrint()

        return output + '|%s\n' % val
 
    def parse(self, line): return octs2str(line).strip().split('|', 2)
