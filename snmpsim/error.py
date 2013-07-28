class SnmpsimError(Exception): pass
class NoDataNotification(SnmpsimError): pass
class MoreDataNotification(SnmpsimError):
    def __init__(self, **kwargs):
        self.__kwargs = kwargs
    def __contains__(self, key): return key in self.__kwargs
    def __getitem__(self, key): return self.__kwargs[key]
    def get(self, key): return self.__kwargs.get(key)
    def keys(self): return self.__kwargs.keys()
