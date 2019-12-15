#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ

from snmpsim.error import SnmpsimError
from snmpsim.grammar import dump
from snmpsim.record import abstract


class DumpRecord(abstract.AbstractRecord):
    grammar = dump.DumpGrammar()
    ext = 'dump'

    def evaluate_oid(self, oid):
        return univ.ObjectIdentifier(oid)

    def evaluate_value(self, oid, tag, value, **context):
        try:
            value = self.grammar.TAG_MAP[tag](value)

        except Exception as exc:
            raise SnmpsimError(
                'value evaluation error for tag %r, value %r: '
                '%s' % (tag, value, exc))

        # not all callers supply the context - just ignore it
        try:
            if (not context['nextFlag'] and
                not context['exactMatch'] or
                    context['setFlag']):
                return context['origOid'], tag, context['errorStatus']

        except KeyError:
            pass

        return oid, tag, value

    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)
        oid = self.evaluate_oid(oid)

        if context.get('oidOnly'):
            value = None

        else:
            try:
                oid, tag, value = self.evaluate_value(
                    oid, tag, value, **context)

            except PyAsn1Error as exc:
                raise SnmpsimError(
                    'value evaluation for %s = %r failed: '
                    '%s\r\n' % (oid, value, exc))

        return oid, value

    def format_oid(self, oid):
        return univ.ObjectIdentifier(oid).prettyPrint()

    def format_value(self, oid, value, **context):
        return self.format_oid(oid), self.grammar.get_tag_by_type(value), str(value)

    def format(self, oid, value, **context):
        return self.grammar.build(*self.format_value(oid, value, **context))
