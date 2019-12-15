#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from snmpsim.error import SnmpsimError
from snmpsim.grammar import abstract


class AbstractRecord(object):
    grammar = abstract.AbstractGrammar()
    ext = ''

    def evaluate_oid(self, oid):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def evaluate_value(self, oid, tag, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def evaluate(self, line, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def format_oid(self, oid):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def format_value(self, oid, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def format(self, oid, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    @staticmethod
    def open(path, flags='rb'):
        return open(path, flags)
