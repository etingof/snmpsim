#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2017, Ilya Etingof <etingof@gmail.com>
# License: http://snmpsim.sf.net/license.html
#
from snmpsim.record import dump
from snmpsim.grammar import mvc


class MvcRecord(dump.DumpRecord):
    grammar = mvc.MvcGrammar()
    ext = 'MVC'  # an alias to .dump
