#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2016, Ilya Etingof <ilya@glas.net>
# License: http://snmpsim.sf.net/license.html
#
from snmpsim.record import dump
from snmpsim.grammar import sap


class SapRecord(dump.DumpRecord):
    grammar = sap.SapGrammar()
    ext = 'sapwalk'
