import os
import sys
import tempfile

if sys.platform[:3] == 'win':
    variation = [
        os.path.join(os.environ['HOMEPATH'], 'SNMP Simulator', 'Variation'),
        os.path.join(os.environ['APPDATA'], 'SNMP Simulator', 'Variation'),
        os.path.join(os.environ['PROGRAMFILES'], 'SNMP Simulator', 'Variation'),
        os.path.join(os.path.split(__file__)[0], 'variation')
    ]
    data = [
        os.path.join(os.environ['HOMEPATH'], 'SNMP Simulator', 'Data'),
        os.path.join(os.environ['APPDATA'], 'SNMP Simulator', 'Data'),
        os.path.join(os.environ['PROGRAMFILES'], 'SNMP Simulator', 'Data'),
        os.path.join(os.path.split(__file__)[0], 'data')
    ]
elif sys.platform == 'darwin':
    variation = [
        os.path.join(os.environ['HOME'], '.snmpsim', 'variation'),
        os.path.join('/', 'usr', 'local', 'share', 'snmpsim', 'variation'),
        os.path.join(sys.prefix, 'snmpsim', 'variation'),
        os.path.join(sys.prefix, 'share', 'snmpsim', 'variation'),
        os.path.join(os.path.split(__file__)[0], 'variation')
    ]
    data = [
        os.path.join(os.environ['HOME'], '.snmpsim', 'data'),
        os.path.join('/', 'usr', 'local', 'share', 'snmpsim', 'data'),
        os.path.join(sys.prefix, 'snmpsim', 'data'),
        os.path.join(sys.prefix, 'share', 'snmpsim', 'data'),
        os.path.join(os.path.split(__file__)[0], 'data')
    ]
else:
    variation = [
        os.path.join(os.environ['HOME'], '.snmpsim', 'variation'),
        os.path.join(sys.prefix, 'snmpsim', 'variation'),
        os.path.join(sys.prefix, 'share', 'snmpsim', 'variation'),
        os.path.join(os.path.split(__file__)[0], 'variation')
    ]
    data = [
        os.path.join(os.environ['HOME'], '.snmpsim', 'data'),
        os.path.join(sys.prefix, 'snmpsim', 'data'),
        os.path.join(sys.prefix, 'share', 'snmpsim', 'data'),
        os.path.join(os.path.split(__file__)[0], 'data')
    ]

cache = os.path.join(tempfile.gettempdir(), 'snmpsim')
