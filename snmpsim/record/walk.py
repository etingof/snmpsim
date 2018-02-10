#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
from snmpsim.record import dump
from snmpsim.grammar import walk


class WalkRecord(dump.DumpRecord):
    grammar = walk.WalkGrammar()
    ext = 'snmpwalk'
