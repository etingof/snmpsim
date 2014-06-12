from pysnmp.proto import rfc1902
from pyasn1.type import univ
from pyasn1.compat.octets import octs2str
from snmpsim.grammar import abstract, dump
from snmpsim import error

class SapGrammar(abstract.AbstractGrammar):
    tagMap = {
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

    def __stringFilter(value):
        if value[:2] == '0x':
            value = [ int(value[x:x+2], 16) for x in range(2, len(value[2:])+2, 2) ]
        return value

    filterMap = {
        'OctetString': __stringFilter
    }

    def parse(self, line):
        try:
            oid, tag, value = [x.strip() for x in octs2str(line).split(',', 2)]
        except:
            raise error.SnmpsimError('broken record <%s>' % line)
        else:
            if oid and tag:
                return oid, tag, self.filterMap.get(tag, lambda x: x)(value.strip())
            raise error.SnmpsimError('broken record <%s>' % line)
