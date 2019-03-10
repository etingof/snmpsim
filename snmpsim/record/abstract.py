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

    def evaluateOid(self, oid):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def evaluateValue(self, oid, tag, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def evaluate(self, line, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def formatOid(self, oid):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def formatValue(self, oid, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)

    def format(self, oid, value, **context):
        raise SnmpsimError(
            'Method not implemented at '
            '%s' % self.__class__.__name__)
