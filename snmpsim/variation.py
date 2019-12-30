#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# Variation module support in simulation data
#
import os

from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pysnmp.smi.error import MibOperationError

from snmpsim import log
from snmpsim.error import NoDataNotification
from snmpsim.error import SnmpsimError
from snmpsim.record import dump
from snmpsim.record import mvc
from snmpsim.record import sap
from snmpsim.record import snmprec
from snmpsim.record import walk
from snmpsim.reporting.manager import ReportingManager

RECORD_TYPES = {
    dump.DumpRecord.ext: dump.DumpRecord(),
    mvc.MvcRecord.ext: mvc.MvcRecord(),
    sap.SapRecord.ext: sap.SapRecord(),
    walk.WalkRecord.ext: walk.WalkRecord(),
}


class SnmprecRecordMixIn(object):

    def evaluate_value(self, oid, tag, value, **context):
        # Variation module reference
        if ':' in tag:
            mod_name, tag = tag[tag.index(':')+1:], tag[:tag.index(':')]

        else:
            mod_name = None

        if mod_name:
            if ('variationModules' in context and
                    mod_name in context['variationModules']):

                if 'dataValidation' in context:
                    return oid, tag, univ.Null

                else:
                    if context['setFlag']:

                        hexvalue = self.grammar.hexify_value(
                            context['origValue'])

                        if hexvalue is not None:
                            context['hexvalue'] = hexvalue
                            context['hextag'] = self.grammar.get_tag_by_type(
                                context['origValue'])
                            context['hextag'] += 'x'

                    # prepare agent and record contexts on first reference
                    (variation_module,
                     agent_contexts,
                     record_contexts) = context['variationModules'][mod_name]

                    if context['dataFile'] not in agent_contexts:
                        agent_contexts[context['dataFile']] = {}

                    if context['dataFile'] not in record_contexts:
                        record_contexts[context['dataFile']] = {}

                    variation_module['agentContext'] = agent_contexts[context['dataFile']]

                    record_contexts = record_contexts[context['dataFile']]

                    if oid not in record_contexts:
                        record_contexts[oid] = {}

                    variation_module['recordContext'] = record_contexts[oid]

                    handler = variation_module['variate']

                    # invoke variation module
                    oid, tag, value = handler(oid, tag, value, **context)

                    ReportingManager.update_metrics(
                        variation=mod_name, variation_call_count=1, **context)

            else:
                ReportingManager.update_metrics(
                    variation=mod_name, variation_failure_count=1, **context)

                raise SnmpsimError(
                    'Variation module "%s" referenced but not '
                    'loaded\r\n' % mod_name)

        if not mod_name:
            if 'dataValidation' in context:
                snmprec.SnmprecRecord.evaluate_value(
                    self, oid, tag, value, **context)

            if (not context['nextFlag'] and
                    not context['exactMatch'] or context['setFlag']):
                return context['origOid'], tag, context['errorStatus']

        if not hasattr(value, 'tagSet'):  # not already a pyasn1 object
            return snmprec.SnmprecRecord.evaluate_value(
                       self, oid, tag, value, **context)

        return oid, tag, value

    def evaluate(self, line, **context):
        oid, tag, value = self.grammar.parse(line)

        oid = self.evaluate_oid(oid)

        if context.get('oidOnly'):
            value = None

        else:
            try:
                oid, tag, value = self.evaluate_value(oid, tag, value, **context)

            except NoDataNotification:
                raise

            except MibOperationError:
                raise

            except PyAsn1Error as exc:
                raise SnmpsimError(
                    'value evaluation for %s = %r failed: '
                    '%s\r\n' % (oid, value, exc))

        return oid, value

    def format_value(self, oid, value, **context):
        (text_oid,
         text_tag,
         text_value) = snmprec.SnmprecRecord.format_value(self, oid, value)

        # invoke variation module
        if context['variationModule']:
            (plain_oid,
             plain_tag,
             plain_value) = snmprec.SnmprecRecord.format_value(
                self, oid, value, nohex=True)

            if plain_tag != text_tag:
                context['hextag'], context['hexvalue'] = text_tag, text_value

            else:
                text_tag, text_value = plain_tag, plain_value

            handler = context['variationModule']['record']

            text_oid, text_tag, text_value = handler(
                text_oid, text_tag, text_value, **context)

        elif 'stopFlag' in context and context['stopFlag']:
            raise NoDataNotification()

        return text_oid, text_tag, text_value


class SnmprecRecord(SnmprecRecordMixIn, snmprec.SnmprecRecord):
    pass


RECORD_TYPES[SnmprecRecord.ext] = SnmprecRecord()


class CompressedSnmprecRecord(
        SnmprecRecordMixIn, snmprec.CompressedSnmprecRecord):
    pass


RECORD_TYPES[CompressedSnmprecRecord.ext] = CompressedSnmprecRecord()


def load_variation_modules(search_path, modules_options):

    variation_modules = {}
    modules_options = modules_options.copy()

    for variation_modules_dir in search_path:
        log.info(
            'Scanning "%s" directory for variation '
            'modules...' % variation_modules_dir)

        if not os.path.exists(variation_modules_dir):
            log.info('Directory "%s" does not exist' % variation_modules_dir)
            continue

        for d_file in os.listdir(variation_modules_dir):
            if d_file[-3:] != '.py':
                continue

            _to_load = []

            mod_name = os.path.splitext(os.path.basename(d_file))[0]

            if mod_name in modules_options:
                while modules_options[mod_name]:
                    alias, params = modules_options[mod_name].pop()
                    _to_load.append((alias, params))

                del modules_options[mod_name]

            else:
                _to_load.append((mod_name, ''))

            mod = os.path.abspath(os.path.join(variation_modules_dir, d_file))

            for alias, params in _to_load:
                if alias in variation_modules:
                    log.error(
                        'ignoring duplicate variation module "%s" at '
                        '"%s"' % (alias, mod))
                    continue

                ctx = {
                    'path': mod,
                    'alias': alias,
                    'args': params,
                    'moduleContext': {}
                }

                try:
                    with open(mod) as fl:
                        exec(compile(fl.read(), mod, 'exec'), ctx)

                except Exception as exc:
                    log.error(
                        'Variation module "%s" execution failure: '
                        '%s' % (mod, exc))
                    return 1

                # moduleContext, agentContexts, recordContexts
                variation_modules[alias] = ctx, {}, {}

        log.info('A total of %s modules found in '
                 '%s' % (len(variation_modules), variation_modules_dir))

    if modules_options:
        log.info('WARNING: unused options for variation modules: '
                '%s' % ', '.join(modules_options))

    return variation_modules


def initialize_variation_modules(variation_modules, mode):
    log.info('Initializing variation modules...')

    for name, modules_contexts in variation_modules.items():

        body = modules_contexts[0]

        for handler in ('init', 'variate', 'shutdown'):
            if handler not in body:
                log.error('missing "%s" handler at variation module '
                          '"%s"' % (handler, name))
                return 1

        try:
            body['init'](options=body['args'], mode=mode)

        except Exception as exc:
            log.error(
                'Variation module "%s" from "%s" load FAILED: '
                '%s' % (body['alias'], body['path'], exc))

        else:
            log.info(
                'Variation module "%s" from "%s" '
                'loaded OK' % (body['alias'], body['path']))


def parse_modules_options(options):
    variation_modules_options = {}

    for option in options:
        args = option.split(':', 1)

        try:
            mod_name, args = args[0], args[1]

        except Exception as exc:
            raise SnmpsimError(
                'ERROR: improper variation module options %s: %s\r\n', exc)

        if '=' in mod_name:
            mod_name, alias = mod_name.split('=', 1)

        else:
            alias = os.path.splitext(os.path.basename(mod_name))[0]

        if mod_name not in variation_modules_options:
            variation_modules_options[mod_name] = []

        variation_modules_options[mod_name].append((alias, args))

    return variation_modules_options
