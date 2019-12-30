#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#

import os
import sys

from snmpsim import confdir
from snmpsim import error
from snmpsim import log
from snmpsim import utils
from snmpsim.record.search.file import get_record

dbm = utils.try_load('anydbm')
if dbm:
    whichdb = utils.try_load('whichdb')

else:
    dbm = utils.try_load('dbm')
    whichdb = dbm


class RecordIndex(object):

    def __init__(self, text_file, text_parser):
        self._text_file = text_file
        self._text_parser = text_parser

        try:
            self._db_file = text_file[:text_file.rindex(os.path.extsep)]

        except ValueError:
            self._db_file = text_file

        self._db_file += os.path.extsep + 'dbm'

        self._db_file = os.path.join(
            confdir.cache, os.path.splitdrive(
                self._db_file)[1].replace(os.path.sep, '_'))

        self._db = self._text = None
        self._db_type = '?'

        self._text_file_time = 0

    def __str__(self):
        return 'Data file %s, %s-indexed, %s' % (
            self._text_file, self._db_type, self._db and 'opened' or 'closed')

    def is_open(self):
        return self._db is not None

    def get_handles(self):
        if self.is_open():
            if self._text_file_time != os.stat(self._text_file)[8]:
                log.info('Text file %s modified, closing' % self._text_file)
                self.close()

        if not self.is_open():
            self.create()
            self.open()

        return self._text, self._db

    @property
    def _db_files(self):
        return (self._db_file + os.path.extsep + 'db',
                self._db_file + os.path.extsep + 'dat',
                self._db_file)

    def create(self, force_index_build=False, validate_data=False):
        text_file_time = os.stat(self._text_file)[8]

        # gdbm on OS X seems to voluntarily append .db, trying to catch that

        index_needed = force_index_build

        for db_file in self._db_files:

            if os.path.exists(db_file):
                if text_file_time < os.stat(db_file)[8]:
                    if index_needed:
                        log.info('Forced index rebuild %s' % db_file)

                    elif not whichdb.whichdb(self._db_file):
                        index_needed = True
                        log.info('Unsupported index format, rebuilding '
                                'index %s' % db_file)

                else:
                    index_needed = True
                    log.info('Index %s out of date' % db_file)

                break

        else:
            index_needed = True
            log.info('Index %s does not exist for data file '
                    '%s' % (self._db_file, self._text_file))

        if index_needed:
            # these might speed-up indexing
            open_flags = 'nfu'

            errors = []

            while open_flags:
                try:
                    db = dbm.open(self._db_file, open_flags)

                except Exception as exc:
                    log.debug('DBM open with flags "%s" failed on file '
                              '%s: %s' % (open_flags, self._db_file, exc))
                    errors.append(str(exc))
                    open_flags = open_flags[:-1]
                    continue

                else:
                    break
            else:
                raise error.SnmpsimError(
                    'Failed to create %s for data file '
                    '%s: %s' % (self._db_file, self._text_file,
                                '; '.join(errors)))

            try:
                text = self._text_parser.open(self._text_file)

            except Exception as exc:
                raise error.SnmpsimError(
                    'Failed to open data file %s: %s' % (self._db_file, exc))

            log.info(
                'Building index %s for data file %s (open flags '
                '"%s")...' % (self._db_file, self._text_file, open_flags))

            sys.stdout.flush()

            line_no = 0
            offset = 0
            prev_offset = -1

            while True:
                line, line_no, offset = get_record(text, line_no, offset)

                if not line:
                    # reference to last OID in data file
                    db['last'] = '%d,%d,%d' % (offset, 0, prev_offset)
                    break

                try:
                    oid, tag, val = self._text_parser.grammar.parse(line)

                except Exception as exc:
                    db.close()

                    for db_file in self._db_files:
                        try:
                            os.remove(db_file)

                        except OSError:
                            pass

                    raise error.SnmpsimError(
                        'Data error at %s:%d:'
                        ' %s' % (self._text_file, line_no, exc))

                if validate_data:
                    try:
                        self._text_parser.evaluate_oid(oid)

                    except Exception as exc:
                        db.close()

                        for db_file in self._db_files:
                            try:
                                os.remove(db_file)

                            except OSError:
                                pass

                        raise error.SnmpsimError(
                            'OID error at %s:%d: %s' % (self._text_file, line_no, exc))

                    try:
                        self._text_parser.evaluate_value(
                            oid, tag, val, dataValidation=True
                        )

                    except Exception as exc:
                        log.info(
                            'ERROR at line %s, value %r: '
                            '%s' % (line_no, val, exc))

                # for lines serving subtrees, type is empty in tag field
                db[oid] = '%d,%d,%d' % (offset, tag[0] == ':', prev_offset)

                if tag[0] == ':':
                    prev_offset = offset

                else:
                    prev_offset = -1   # not a subtree - no back reference

                offset += len(line)

            text.close()
            db.close()

            log.info('...%d entries indexed' % line_no)

        self._text_file_time = os.stat(self._text_file)[8]

        self._db_type = whichdb.whichdb(self._db_file)

        return self

    def lookup(self, oid):
        return self._db[oid]

    def open(self):
        self._text = self._text_parser.open(self._text_file)
        self._db = dbm.open(self._db_file)

    def close(self):
        self._text.close()
        self._db.close()
        self._db = self._text = None
