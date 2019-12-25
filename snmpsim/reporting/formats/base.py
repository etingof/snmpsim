#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/snmpsim/license.html
#
# SNMP Agent Simulator
#


class BaseReporter(object):
    """Maintain activity metrics.
    """
    def update_metrics(self, **kwargs):
        """Process activity update.
        """

    def flush(self):
        """Dump accumulated metrics into a JSON file.

        Reset all counters upon success.
        """

    def __str__(self):
        return self.__class__.__name__