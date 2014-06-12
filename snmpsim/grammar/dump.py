from pysnmp.proto import rfc1902
from pyasn1.type import univ
from pyasn1.compat.octets import octs2str
from snmpsim.grammar import abstract
from snmpsim import error

class DumpGrammar(abstract.AbstractGrammar):
    tagMap = {
        '0': rfc1902.Counter32,
        '1': rfc1902.Gauge32,
        '2': rfc1902.Integer32,
        '3': rfc1902.IpAddress,
        '4': univ.Null,
        '5': univ.ObjectIdentifier,
        '6': rfc1902.OctetString,
        '7': rfc1902.TimeTicks,
        '8': rfc1902.Counter32,  # an alias
        '9': rfc1902.Counter64,
    }

    def __nullFilter(value):
        return '' # simply drop whatever value is there when it's a Null
    
    def __unhexFilter(value):
        if value[:5].lower() == 'hex: ':
            value = [ int(x, 16) for x in value[5:].split('.') ]
        elif value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        return value

    filterMap = {
        '4': __nullFilter,
        '6': __unhexFilter
    }

    def parse(self, line):
        try:
            oid, tag, value = octs2str(line).split('|', 2)
        except:
            raise error.SnmpsimError('broken record <%s>' % line)
        else:
            if oid and tag:
                return oid, tag, self.filterMap.get(tag, lambda x: x)(value.strip())
            raise error.SnmpsimError('broken record <%s>' % line)

