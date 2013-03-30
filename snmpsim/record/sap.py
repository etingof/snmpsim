from snmpsim.record import dump
from snmpsim.grammar import sap

class SapRecord(dump.DumpRecord):
    grammar = sap.SapGrammar()
    ext = 'sapwalk'
