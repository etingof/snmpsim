#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from snmpsim import error


class AbstractGrammar:
    def parse(self, line):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                 self.__class__.__name__)

    def build(self, oid, tag, val):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                 self.__class__.__name__)

    def getTagByType(self, val):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                 self.__class__.__name__)
