from snmpsim.record import dump
from snmpsim.grammar import snmprec
from snmpsim import error

class SnmprecRecord(dump.DumpRecord):
    grammar = snmprec.SnmprecGrammar()
    ext = 'snmprec'

    def evaluateValue(self, oid, tag, value, **context):
        if tag and tag[-1] == 'x':
            tag = tag[:-1]
            hexvalue = value
        else:
            hexvalue = None

        try:
            if hexvalue is None:
                return oid, tag, self.grammar.tagMap[tag](value)
            else:
                return oid, tag, self.grammar.tagMap[tag](hexValue=hexvalue)
        except:
            raise error.SnmpsimError('value evaluation error for tag %r, value %r' % (tag, value))

    def formatValue(self, oid, value, **context):
        if 'nohex' in context and context['nohex']:
            hexvalue = None
        else:
            hexvalue = self.grammar.hexifyValue(value)

        textTag = self.grammar.getTagByType(value)

        if hexvalue:
            textTag, textValue = textTag + 'x', hexvalue
        else:
            textTag, textValue = textTag, str(value)

        return self.formatOid(oid), textTag, textValue
