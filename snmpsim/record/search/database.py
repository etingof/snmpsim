import os
import sys
if sys.version_info[0] < 3:
    import anydbm as dbm
    from whichdb import whichdb
else:
    import dbm
    whichdb = dbm.whichdb
from snmpsim import confdir, log, error
from snmpsim.record.search.file import getRecord

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

        self.__textFileTime = 0

    def __str__(self):
        return 'Data file %s, %s-indexed, %s' % (
            self.__textFile, self.__dbType, self.__db and 'opened' or 'closed'
        )

    def isOpen(self): return self.__db is not None

    def getHandles(self):
        if self.isOpen():
            if self.__textFileTime != os.stat(self.__textFile)[8]:
                log.msg('Text file %s modified, closing' % self.__textFile)
                self.close()
        if not self.isOpen():
            self.create()
            self.open()
        return self.__text, self.__db

    def create(self, forceIndexBuild=False, validateData=False):
        textFileTime = os.stat(self.__textFile)[8]

        # gdbm on OS X seems to voluntarily append .db, trying to catch that
        
        indexNeeded = forceIndexBuild
        
        for dbFile in (
            self.__dbFile + os.path.extsep + 'db',
            self.__dbFile
            ):
            if os.path.exists(dbFile):
                if textFileTime < os.stat(dbFile)[8]:
                    if indexNeeded:
                        log.msg('Forced index rebuild %s' % dbFile)
                    elif not whichdb(dbFile):
                        indexNeeded = True
                        log.msg('Unsupported index format, rebuilding index %s' % dbFile)
                else:
                    indexNeeded = True
                    log.msg('Index %s out of date' % dbFile)
                break
        else:
            indexNeeded = True
            log.msg('Index %s does not exist for data file %s' % (self.__dbFile, self.__textFile))
            
        if indexNeeded:
            # these might speed-up indexing
            open_flags = 'nfu' 
            while open_flags:
                try:
                    db = dbm.open(self.__dbFile, open_flags)
                except Exception:
                    open_flags = open_flags[:-1]
                    continue
                else:
                    break
            else:
                raise error.SnmpsimError('Failed to create %s for data file %s: %s' % (self.__dbFile, self.__textFile, sys.exc_info()[1]))

            try:
                text = open(self.__textFile, 'rb')
            except:
                raise error.SnmpsimError('Failed to open data file %s: %s' % (self.__dbFile, sys.exc_info()[0]))

            log.msg('Building index %s for data file %s (open flags \"%s\")...' % (self.__dbFile, self.__textFile, open_flags))
            sys.stdout.flush()
        
            lineNo = 0
            offset = 0
            prevOffset = -1
            while 1:
                line, lineNo, offset = getRecord(text, lineNo, offset)
                if not line:
                    # reference to last OID in data file
                    db['last'] = '%d,%d,%d' % (offset, 0, prevOffset)
                    break
             
                try:
                    oid, tag, val = self.__textParser.grammar.parse(line)
                except Exception:
                    db.close()
                    exc = sys.exc_info()[1]
                    try:
                        os.remove(self.__dbFile)
                    except OSError:
                        pass
                    raise error.SnmpsimError('Data error at %s:%d: %s' % (self.__textFile, lineNo, exc))

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
                        raise error.SnmpsimError('OID error at %s:%d: %s' % (self.__textFile, lineNo, exc))
                    try:
                        self.__textParser.evaluateValue(
                            oid, tag, val, dataValidation=True
                        )
                    except Exception:
                        log.msg(
                            'ERROR at line %s, value %r: %s' % \
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
       
            log.msg('...%d entries indexed' % lineNo)

        self.__textFileTime = os.stat(self.__textFile)[8]

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
