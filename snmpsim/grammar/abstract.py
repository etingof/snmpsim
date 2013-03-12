from snmpsim import error

class AbstractGrammar:
    def parse(self, line):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)

    def build(self, oid, val):
        raise error.SnmpsimError('Method not implemented at %s' % \
                                  self.__class__.__name__)
