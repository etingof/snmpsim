from snmpsim.grammar import abstract
from snmpsim.error import SnmpsimError

class AbstractRecord:
    grammar = abstract.AbstractGrammar()
    ext = ''

    def evaluateOid(self, oid):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

    def evaluateValue(self, oid, tag, value, **context):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)
    
    def evaluate(self, line, **context):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

    def formatOid(self, oid):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

    def formatValue(self, oid, value, **context):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

    def format(self, oid, value, **context):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

