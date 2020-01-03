#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#
from snmpsim import error
from snmpsim.reporting.formats import alljson
from snmpsim.reporting.formats import null
from snmpsim import log


class ReportingManager(object):
    """Maintain activity metrics.

    Accumulates and periodically dumps activity metrics reflecting
    SNMP command responder activity.

    These counters are accumulated in memory for some time, then get
    written down as a JSON file indexed by time. Consumers are expected
    to process each of these files and are free to remove them.
    """

    REPORTERS = {
        'null': null.NullReporter,
        'fulljson': alljson.FullJsonReporter,
        'minimaljson': alljson.MinimalJsonReporter,
    }

    _reporter = null.NullReporter()

    @classmethod
    def configure(cls, fmt, *args):
        try:
            reporter = cls.REPORTERS[fmt]

        except KeyError:
            raise error.SnmpsimError('Unsupported reporting format: %s' % fmt)

        cls._reporter = reporter(*args)

        log.info('Using "%s" activity reporting method with '
                 'params %s' % (cls._reporter, ', '.join(args)))

    @classmethod
    def update_metrics(cls, **kwargs):

        cls._reporter.update_metrics(**kwargs)
        cls._reporter.flush()
