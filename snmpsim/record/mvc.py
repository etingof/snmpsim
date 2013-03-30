from snmpsim.record import dump
from snmpsim.grammar import mvc

class MvcRecord(dump.DumpRecord):
    grammar = mvc.MvcGrammar()
    ext = 'MVC'  # an alias to .dump
