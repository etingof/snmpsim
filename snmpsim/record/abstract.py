from snmpsim.grammar import abstract
from snmpsim.error import SnmpsimError

class AbstractRecord:
    grammar = abstract.AbstractGrammar()
    ext = ''

    def evaluateOid(self, oid):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)

    def evaluateValue(self, oid, tag, value, **context):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)
    
    def evaluate(self, line, **context):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)

    def formatOid(self, oid):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)

    def formatValue(self, oid, value, **context):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)

    def format(self, oid, value, **context):
        raise SnmpsimError('Method not implemented at %s' % \
                            self.__class__.__name__)

