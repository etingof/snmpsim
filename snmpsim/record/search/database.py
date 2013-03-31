import os
import sys
if sys.version_info[0] < 3:
    import anydbm as dbm
    from whichdb import whichdb
else:
    import dbm
    whichdb = dbm.whichdb
from snmpsim import confdir

class RecordIndex:
    def __init__(self, textFile, textParser):
        self.__textFile = textFile
        self.__textParser = textParser
        try:
            self.__dbFile = textFile[:textFile.rindex(os.path.extsep)]
        except ValueError:
            self.__dbFile = textFile

        self.__dbFile = self.__dbFile + os.path.extsep + 'dbm'
   
        self.__dbFile = os.path.join(confdir.cache, os.path.splitdrive(self.__dbFile)[1].replace(os.path.sep, '_'))
         
        self.__db = self.__text = None
        self.__dbType = '?'

    def __str__(self):
        return 'Data file %s, %s-indexed, %s' % (
            self.__textFile, self.__dbType, self.__db and 'opened' or 'closed'
        )

    def isOpen(self): return self.__db is not None

    def getHandles(self):
        if not self.isOpen():
            self.open()
        return self.__text, self.__db

    def create(self, forceIndexBuild=False, validateData=False):
        textFileStamp = os.stat(self.__textFile)[8]

        # gdbm on OS X seems to voluntarily append .db, trying to catch that
        
        indexNeeded = forceIndexBuild
        
        for dbFile in (
            self.__dbFile + os.path.extsep + 'db',
            self.__dbFile
            ):
            if os.path.exists(dbFile):
                if textFileStamp < os.stat(dbFile)[8]:
                    if indexNeeded:
                        sys.stdout.write('Forced index rebuild %s\r\n' % dbFile)
                    elif not whichdb(dbFile):
                        indexNeeded = True
                        sys.stdout.write('Unsupported index format, rebuilding index %s\r\n' % dbFile)
                else:
                    indexNeeded = True
                    sys.stdout.write('Index %s out of date\r\n' % dbFile)
                break
        else:
            indexNeeded = True
            sys.stdout.write('Index %s does not exist for data file %s\r\n' % (self.__dbFile, self.__textFile))
            
        if indexNeeded:
            # these might speed-up indexing
            open_flags = 'nfu' 
            while open_flags:
                try:
                    db = dbm.open(self.__dbFile, open_flags)
                except Exception:
                    open_flags = open_flags[:-1]
                    if not open_flags:
                        raise
                else:
                    break

            text = open(self.__textFile, 'rb')

            sys.stdout.write('Building index %s for data file %s (open flags \"%s\")...' % (self.__dbFile, self.__textFile, open_flags))
            sys.stdout.flush()
        
            lineNo = 0
            offset = 0
            prevOffset = -1
            while 1:
                line = text.readline()
                if not line:
                    break
            
                lineNo += 1

                try:
                    oid, tag, val = self.__textParser.grammar.parse(line)
                except Exception:
                    db.close()
                    exc = sys.exc_info()[1]
                    try:
                        os.remove(self.__dbFile)
                    except OSError:
                        pass
                    raise Exception(
                        'Data error at %s:%d: %s' % (
                            self.__textFile, lineNo, exc
                            )
                        )

                if validateData:
                    try:
                        self.__textParser.evaluateOid(oid)
                    except Exception:
                        db.close()
                        exc = sys.exc_info()[1]
                        try:
                            os.remove(self.__dbFile)
                        except OSError:
                            pass
                        raise Exception(
                            'OID error at %s:%d: %s' % (
                                self.__textFile, lineNo, exc
                                )
                            )
                    try:
                        self.__textParser.evaluateValue(
                            oid, tag, val, dataValidation=True
                        )
                    except Exception:
                        sys.stdout.write(
                            '\r\n*** Error at line %s, value %r: %s\r\n' % \
                            (lineNo, val, sys.exc_info()[1])
                            )

                # for lines serving subtrees, type is empty in tag field
                db[oid] = '%d,%d,%d' % (offset, tag[0] == ':', prevOffset)

                if tag[0] == ':':
                    prevOffset = offset
                else:
                    prevOffset = -1   # not a subtree - no backreference

                offset += len(line)

            text.close()
            db.close()
        
            sys.stdout.write('...%d entries indexed\r\n' % (lineNo - 1,))

        self.__dbType = whichdb(self.__dbFile)

        return self

    def lookup(self, oid): return self.__db[oid]

    def open(self):
        self.__text = open(self.__textFile, 'rb')
        self.__db = dbm.open(self.__dbFile)

    def close(self):
        self.__text.close()
        self.__db.close()
        self.__db = self.__text = None
