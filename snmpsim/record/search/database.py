#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
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


class RecordIndex(object):

    def __init__(self, textFile, textParser):
        self._textFile = textFile
        self._textParser = textParser

        try:
            self._dbFile = textFile[:textFile.rindex(os.path.extsep)]

        except ValueError:
            self._dbFile = textFile

        self._dbFile += os.path.extsep + 'dbm'

        self._dbFile = os.path.join(
            confdir.cache, os.path.splitdrive(
                self._dbFile)[1].replace(os.path.sep, '_'))

        self._db = self.__text = None
        self._dbType = '?'

        self._textFileTime = 0

    def __str__(self):
        return 'Data file %s, %s-indexed, %s' % (
            self._textFile, self._dbType, self._db and 'opened' or 'closed'
        )

    def isOpen(self):
        return self._db is not None

    def getHandles(self):
        if self.isOpen():
            if self._textFileTime != os.stat(self._textFile)[8]:
                log.msg('Text file %s modified, closing' % self._textFile)
                self.close()

        if not self.isOpen():
            self.create()
            self.open()

        return self.__text, self._db

    @property
    def _dbFiles(self):
        return (self._dbFile + os.path.extsep + 'db',
                self._dbFile + os.path.extsep + 'dat',
                self._dbFile)

    def create(self, forceIndexBuild=False, validateData=False):
        textFileTime = os.stat(self._textFile)[8]

        # gdbm on OS X seems to voluntarily append .db, trying to catch that

        indexNeeded = forceIndexBuild

        for dbFile in self._dbFiles:

            if os.path.exists(dbFile):
                if textFileTime < os.stat(dbFile)[8]:
                    if indexNeeded:
                        log.msg('Forced index rebuild %s' % dbFile)

                    elif not whichdb(self._dbFile):
                        indexNeeded = True
                        log.msg('Unsupported index format, rebuilding '
                                'index %s' % dbFile)

                else:
                    indexNeeded = True
                    log.msg('Index %s out of date' % dbFile)

                break

        else:
            indexNeeded = True
            log.msg('Index %s does not exist for data file '
                    '%s' % (self._dbFile, self._textFile))

        if indexNeeded:
            # these might speed-up indexing
            open_flags = 'nfu'

            while open_flags:
                try:
                    db = dbm.open(self._dbFile, open_flags)

                except Exception:
                    open_flags = open_flags[:-1]
                    continue

                else:
                    break
            else:
                raise error.SnmpsimError(
                    'Failed to create %s for data file %s: '
                    '%s' % (self._dbFile, self._textFile, sys.exc_info()[1]))

            try:
                text = self._textParser.open(self._textFile)

            except Exception:
                raise error.SnmpsimError(
                    'Failed to open data file %s: '
                    '%s' % (self._dbFile, sys.exc_info()[0]))

            log.msg(
                'Building index %s for data file %s (open flags '
                '\"%s\")...' % (self._dbFile, self._textFile, open_flags))

            sys.stdout.flush()

            lineNo = 0
            offset = 0
            prevOffset = -1

            while True:
                line, lineNo, offset = getRecord(text, lineNo, offset)

                if not line:
                    # reference to last OID in data file
                    db['last'] = '%d,%d,%d' % (offset, 0, prevOffset)
                    break

                try:
                    oid, tag, val = self._textParser.grammar.parse(line)

                except Exception:
                    db.close()
                    exc = sys.exc_info()[1]

                    for dbFile in self._dbFiles:
                        try:
                            os.remove(dbFile)

                        except OSError:
                            pass

                    raise error.SnmpsimError(
                        'Data error at %s:%d:'
                        ' %s' % (self._textFile, lineNo, exc))

                if validateData:
                    try:
                        self._textParser.evaluateOid(oid)

                    except Exception:
                        db.close()
                        exc = sys.exc_info()[1]

                        for dbFile in self._dbFiles:
                            try:
                                os.remove(dbFile)

                            except OSError:
                                pass

                        raise error.SnmpsimError(
                            'OID error at %s:%d: %s' % (self._textFile, lineNo, exc))

                    try:
                        self._textParser.evaluateValue(
                            oid, tag, val, dataValidation=True
                        )

                    except Exception:
                        log.msg(
                            'ERROR at line %s, value %r: '
                            '%s' % (lineNo, val, sys.exc_info()[1]))

                # for lines serving subtrees, type is empty in tag field
                db[oid] = '%d,%d,%d' % (offset, tag[0] == ':', prevOffset)

                if tag[0] == ':':
                    prevOffset = offset

                else:
                    prevOffset = -1   # not a subtree - no back reference

                offset += len(line)

            text.close()
            db.close()

            log.msg('...%d entries indexed' % lineNo)

        self._textFileTime = os.stat(self._textFile)[8]

        self._dbType = whichdb(self._dbFile)

        return self

    def lookup(self, oid):
        return self._db[oid]

    def open(self):
        self.__text = self._textParser.open(self._textFile)
        self._db = dbm.open(self._dbFile)

    def close(self):
        self.__text.close()
        self._db.close()
        self._db = self.__text = None
