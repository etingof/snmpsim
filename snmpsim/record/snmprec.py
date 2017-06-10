#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2017, Ilya Etingof <etingof@gmail.com>
# License: http://snmpsim.sf.net/license.html
#
try:
    import ast

except ImportError:
    ast = None

from snmpsim.record import dump
from snmpsim.grammar import snmprec
from snmpsim import error


class SnmprecRecord(dump.DumpRecord):
    grammar = snmprec.SnmprecGrammar()
    ext = 'snmprec'

    def unpackTag(self, tag):
        if tag.endswith('x') or tag.endswith('e'):
            return tag[:-1], tag[-1]
        else:
            return tag, None

    def evaluateValue(self, oid, tag, value, **context):
        tag, encodingId = self.unpackTag(tag)

        try:
            if encodingId == 'e':
                try:
                    value = ast.literal_eval(value)
                except:
                    raise error.SnmpsimError('Interpreting Python escapes require Python 2.6+')

                return oid, tag, self.grammar.tagMap[tag](value)
            elif encodingId == 'x':
                return oid, tag, self.grammar.tagMap[tag](hexValue=value)
            else:
                return oid, tag, self.grammar.tagMap[tag](value)

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
            try:
                textValue = str(value.asOctets())
                if textValue.startswith('b'):
                    textValue = textValue[1:]

                textTag += 'e'

            except AttributeError:
                textValue = str(value)

        return self.formatOid(oid), textTag, textValue
