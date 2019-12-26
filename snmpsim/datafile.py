#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# Simulation data file management tools
#
import os
import stat

from pyasn1.compat.octets import str2octs
from pyasn1.type import univ
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.carrier.asyncore.dgram import unix
from pysnmp.proto import rfc1902
from pysnmp.smi import exval
from pysnmp.smi.error import MibOperationError

from snmpsim import log
from snmpsim import variation
from snmpsim.error import NoDataNotification
from snmpsim.error import SnmpsimError
from snmpsim.record.search.database import RecordIndex
from snmpsim.record.search.file import get_record
from snmpsim.record.search.file import search_record_by_oid
from snmpsim.reporting.manager import ReportingManager

SELF_LABEL = 'self'


class AbstractLayout(object):
    layout = '?'


class DataFile(AbstractLayout):
    layout = 'text'
    opened_queue = []
    max_queue_entries = 31  # max number of open text and index files

    def __init__(self, textFile, textParser, variationModules):
        self._record_index = RecordIndex(textFile, textParser)
        self._text_parser = textParser
        self._text_file = textFile
        self._variation_modules = variationModules

    def index_text(self, forceIndexBuild=False, validateData=False):
        self._record_index.create(forceIndexBuild, validateData)
        return self

    def close(self):
        self._record_index.close()

    def get_handles(self):
        if not self._record_index.is_open():
            if len(DataFile.opened_queue) > self.max_queue_entries:
                log.info('Closing %s' % self)
                DataFile.opened_queue[0].close()
                del DataFile.opened_queue[0]

            DataFile.opened_queue.append(self)

            log.info('Opening %s' % self)

        return self._record_index.get_handles()

    def process_var_binds(self, var_binds, **context):
        rsp_var_binds = []

        if context.get('nextFlag'):
            error_status = exval.endOfMib

        else:
            error_status = exval.noSuchInstance

        try:
            text, db = self.get_handles()

        except SnmpsimError as exc:
            log.error(
                'Problem with data file or its index: %s' % exc)

            ReportingManager.update_metrics(
                data_file=self._text_file, datafile_failure_count=1,
                transport_call_count=1, **context)

            return [(vb[0], error_status) for vb in var_binds]

        vars_remaining = vars_total = len(var_binds)
        err_total = 0

        log.info(
            'Request var-binds: %s, flags: %s, '
            '%s' % (', '.join(['%s=<%s>' % (vb[0], vb[1].prettyPrint())
                               for vb in var_binds]),
                    context.get('nextFlag') and 'NEXT' or 'EXACT',
                    context.get('setFlag') and 'SET' or 'GET'))

        for oid, val in var_binds:
            text_oid = str(univ.OctetString('.'.join(['%s' % x for x in oid])))

            try:
                line = self._record_index.lookup(
                    str(univ.OctetString('.'.join(['%s' % x for x in oid]))))

            except KeyError:
                offset = search_record_by_oid(oid, text, self._text_parser)
                subtree_flag = exact_match = False

            else:
                offset, subtree_flag, prev_offset = line.split(str2octs(','), 2)
                subtree_flag, exact_match = int(subtree_flag), True

            offset = int(offset)

            text.seek(offset)

            vars_remaining -= 1

            line, _, _ = get_record(text)  # matched line

            while True:
                if exact_match:
                    if context.get('nextFlag') and not subtree_flag:

                        _next_line, _, _ = get_record(text)  # next line

                        if _next_line:
                            _next_oid, _ = self._text_parser.evaluate(
                                _next_line, oidOnly=True)

                            try:
                                _, subtree_flag, _ = self._record_index.lookup(
                                    str(_next_oid)).split(str2octs(','), 2)

                            except KeyError:
                                log.error(
                                    'data error for %s at %s, index '
                                    'broken?' % (self, _next_oid))
                                line = ''  # fatal error

                            else:
                                subtree_flag = int(subtree_flag)
                                line = _next_line

                        else:
                            line = _next_line

                else:  # search function above always rounds up to the next OID
                    if line:
                        _oid, _ = self._text_parser.evaluate(
                            line, oidOnly=True
                        )

                    else:  # eom
                        _oid = 'last'

                    try:
                        _, _, _prev_offset = self._record_index.lookup(
                            str(_oid)).split(str2octs(','), 2)

                    except KeyError:
                        log.error(
                            'data error for %s at %s, index '
                            'broken?' % (self, _oid))
                        line = ''  # fatal error

                    else:
                        _prev_offset = int(_prev_offset)

                        # previous line serves a subtree?
                        if _prev_offset >= 0:
                            text.seek(_prev_offset)
                            _prev_line, _, _ = get_record(text)
                            _prev_oid, _ = self._text_parser.evaluate(
                                _prev_line, oidOnly=True)

                            if _prev_oid.isPrefixOf(oid):
                                # use previous line to the matched one
                                line = _prev_line
                                subtree_flag = True

                if not line:
                    _oid = oid
                    _val = error_status
                    break

                call_context = context.copy()
                call_context.update(
                    (),
                    origOid=oid,
                    origValue=val,
                    dataFile=self._text_file,
                    subtreeFlag=subtree_flag,
                    exactMatch=exact_match,
                    errorStatus=error_status,
                    varsTotal=vars_total,
                    varsRemaining=vars_remaining,
                    variationModules=self._variation_modules
                )

                try:
                    _oid, _val = self._text_parser.evaluate(
                        line, **call_context)

                    if _val is exval.endOfMib:
                        exact_match = True
                        subtree_flag = False
                        continue

                except NoDataNotification:
                    raise

                except MibOperationError:
                    raise

                except Exception as exc:
                    _oid = oid
                    _val = error_status
                    err_total += 1
                    log.error(
                        'data error at %s for %s: %s' % (self, text_oid, exc))

                break

            rsp_var_binds.append((_oid, _val))

        log.info(
            'Response var-binds: %s' % (
                ', '.join(['%s=<%s>' % (
                    vb[0], vb[1].prettyPrint()) for vb in rsp_var_binds])))

        ReportingManager.update_metrics(
            data_file=self._text_file, varbind_count=vars_total,
            datafile_call_count=1, datafile_failure_count=err_total,
            transport_call_count=1,
            **context)

        return rsp_var_binds

    def __str__(self):
        return '%s controller' % self._text_file


def get_data_files(tgt_dir, top_len=None):
    if top_len is None:
        top_len = len(tgt_dir.split(os.path.sep))

    dir_content = []

    for d_file in os.listdir(tgt_dir):
        full_path = os.path.join(tgt_dir, d_file)

        inode = os.lstat(full_path)

        if stat.S_ISLNK(inode.st_mode):
            rel_path = full_path.split(os.path.sep)[top_len:]
            full_path = os.readlink(full_path)

            if not os.path.isabs(full_path):
                full_path = os.path.join(tgt_dir, full_path)

            inode = os.stat(full_path)

        else:
            rel_path = full_path.split(os.path.sep)[top_len:]

        if stat.S_ISDIR(inode.st_mode):
            dir_content += get_data_files(full_path, top_len)
            continue

        if not stat.S_ISREG(inode.st_mode):
            continue

        for dExt in variation.RECORD_TYPES:
            if d_file.endswith(dExt):
                break

        else:
            continue

        # just the file name would serve for agent identification
        if rel_path[0] == SELF_LABEL:
            rel_path = rel_path[1:]

        if len(rel_path) == 1 and rel_path[0] == SELF_LABEL + os.path.extsep + dExt:
            rel_path[0] = rel_path[0][4:]

        ident = os.path.join(*rel_path)
        ident = ident[:-len(dExt) - 1]
        ident = ident.replace(os.path.sep, '/')

        dir_content.append(
            (full_path,
             variation.RECORD_TYPES[dExt],
             ident)
        )

    return dir_content


def probe_context(transport_domain, transport_address,
                  context_engine_id, context_name):
    """Suggest variations of context name based on request data
    """
    if context_engine_id:
        candidate = [
            context_engine_id, context_name, '.'.join(
                [str(x) for x in transport_domain])]

    else:
        # try legacy layout w/o contextEngineId in the path
        candidate = [
            context_name, '.'.join(
                [str(x) for x in transport_domain])]

    if transport_domain[:len(udp.domainName)] == udp.domainName:
        candidate.append(transport_address[0])

    elif udp6 and transport_domain[:len(udp6.domainName)] == udp6.domainName:
        candidate.append(str(transport_address[0]).replace(':', '_'))

    elif unix and transport_domain[:len(unix.domainName)] == unix.domainName:
        candidate.append(transport_address)

    candidate = [str(x) for x in candidate if x]

    while candidate:
        yield rfc1902.OctetString(
            os.path.normpath(
                os.path.sep.join(candidate)).replace(os.path.sep, '/')).asOctets()
        del candidate[-1]

    # try legacy layout w/o contextEngineId in the path
    if context_engine_id:
        for candidate in probe_context(
                transport_domain, transport_address, None, context_name):
            yield candidate
