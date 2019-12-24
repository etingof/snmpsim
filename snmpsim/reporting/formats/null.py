#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#
from snmpsim.reporting.formats import base


class NullReporter(base.BaseReporter):
    """Maintain activity metrics.
    """
