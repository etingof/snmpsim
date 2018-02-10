#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from snmpsim.record import dump
from snmpsim.grammar import mvc


class MvcRecord(dump.DumpRecord):
    grammar = mvc.MvcGrammar()
    ext = 'MVC'  # an alias to .dump
