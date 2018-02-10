#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from snmpsim.record import dump
from snmpsim.grammar import snmprec
from snmpsim import error


class SnmprecRecord(dump.DumpRecord):
    grammar = snmprec.SnmprecGrammar()
    ext = 'snmprec'

    # https://docs.python.org/3/reference/lexical_analysis.html#literals
    ESCAPE_CHARS = {
        92: 92,
        39: 39,
        34: 34,
        97: 7,
        98: 8,
        102: 12,
        110: 10,
        114: 13,
        116: 9,
        118: 11,
    }

    def unpackTag(self, tag):
        if tag.endswith('x') or tag.endswith('e'):
            return tag[:-1], tag[-1]

        else:
            return tag, None

    def evaluateRawString(self, escaped):
        """Evaluates raw Python string like `ast.literal_eval` does"""
        unescaped = []
        hexdigit = None
        escape = False

        for char in escaped:

            number = ord(char)

            if hexdigit is not None:
                if hexdigit:
                    number = (int(hexdigit, 16) << 4) + int(char, 16)
                    hexdigit = None

                else:
                    hexdigit = char
                    continue

            if escape:
                escape = False

                try:
                    number = self.ESCAPE_CHARS[number]

                except KeyError:
                    if number == 120:
                        hexdigit = ''
                        continue

                    raise ValueError('Unknown escape character %c' % char)

            if number == 92:  # '\'
                escape = True
                continue

            unescaped.append(number)

        return unescaped

    def evaluateValue(self, oid, tag, value, **context):
        tag, encodingId = self.unpackTag(tag)

        try:
            if encodingId == 'e':

                value = self.evaluateRawString(value)

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
                textValue = repr(value.asOctets())

                if textValue.startswith('b'):
                    textValue = textValue[1:]

                textValue = textValue[1:-1]

                if '\\' in textValue:
                    textTag += 'e'

            except AttributeError:
                textValue = str(value)

        return self.formatOid(oid), textTag, textValue
