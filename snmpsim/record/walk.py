from snmpsim.record import dump
from snmpsim.grammar import walk

class WalkRecord(dump.DumpRecord):
    grammar = walk.WalkGrammar()
    ext = 'snmpwalk'
