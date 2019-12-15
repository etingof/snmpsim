#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
import bz2

from snmpsim import error
from snmpsim.grammar import snmprec
from snmpsim.record import dump

from pyasn1.compat import octets


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

    @staticmethod
    def unpack_tag(tag):
        if tag.endswith('x') or tag.endswith('e'):
            return tag[:-1], tag[-1]

        else:
            return tag, None

    def evaluate_raw_string(self, escaped):
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

            elif number == 92:  # '\'
                escape = True
                continue

            unescaped.append(number)

        return unescaped

    def evaluate_value(self, oid, tag, value, **context):
        tag, encoding_id = self.unpack_tag(tag)

        try:
            if encoding_id == 'e':

                value = self.evaluate_raw_string(value)

                return oid, tag, self.grammar.TAG_MAP[tag](value)

            elif encoding_id == 'x':
                if octets.isOctetsType(value):
                    value = octets.octs2str(value)

                return oid, tag, self.grammar.TAG_MAP[tag](hexValue=value)

            else:
                return oid, tag, self.grammar.TAG_MAP[tag](value)

        except Exception as exc:
            raise error.SnmpsimError(
                'value evaluation error for tag %r, value '
                '%r: %s' % (tag, value, exc))

    def format_value(self, oid, value, **context):
        if 'nohex' in context and context['nohex']:
            hexvalue = None

        else:
            hexvalue = self.grammar.hexify_value(value)

        text_tag = self.grammar.get_tag_by_type(value)

        if hexvalue:
            text_tag, text_value = text_tag + 'x', hexvalue

        else:
            try:
                text_value = repr(value.asOctets())

                if text_value.startswith('b'):
                    text_value = text_value[1:]

                text_value = text_value[1:-1]

                if '\\' in text_value:
                    text_tag += 'e'

            except AttributeError:
                text_value = str(value)

        return self.format_oid(oid), text_tag, text_value


class CompressedSnmprecRecord(SnmprecRecord):
    ext = 'snmprec.bz2'

    @staticmethod
    def open(path, flags='rb'):
        return bz2.BZ2File(path, flags)
