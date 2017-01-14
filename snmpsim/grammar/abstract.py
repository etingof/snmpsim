#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2017, Ilya Etingof <etingof@gmail.com>
# License: http://snmpsim.sf.net/license.html
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
