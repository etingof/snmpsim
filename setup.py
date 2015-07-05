#!/usr/bin/env python
"""SNMP Agents simulator

   SNMP Simulator is a tool that acts as multitude of SNMP Agents built
   into real physical devices, from SNMP Manager's point of view.
   Simulator builds and uses a database of physical devices' SNMP footprints 
   to respond like their original counterparts do.
"""
import sys
import os
import glob

classifiers = """\
Development Status :: 5 - Production/Stable
Environment :: Console
Intended Audience :: Developers
Intended Audience :: Education
Intended Audience :: Information Technology
Intended Audience :: Science/Research
Intended Audience :: System Administrators
Intended Audience :: Telecommunications Industry
License :: OSI Approved :: BSD License
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python :: 2
Programming Language :: Python :: 3
Topic :: Communications
Topic :: System :: Monitoring
Topic :: System :: Networking :: Monitoring
"""

def howto_install_setuptools():
    print("""
   Error: You need setuptools Python package!

   It's very easy to install it, just type (as root on Linux):

   wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
   python ez_setup.py

   Then you could make eggs from this package.
""")

if sys.version_info[:2] < (2, 4):
    print("ERROR: this package requires Python 2.4 or later!")
    sys.exit(1)

try:
    from setuptools import setup
    params = {
        'install_requires': [ 'pysnmp>=4.3.0' ],
        'zip_safe': False  # this is due to data and variation dirs
        }
except ImportError:
    for arg in sys.argv:
        if 'egg' in arg:
            howto_install_setuptools()
            sys.exit(1)
    from distutils.core import setup
    params = {}
    if sys.version_info[:2] > (2, 4):
        params['requires'] = [ 'pysnmp(>=4.3.0)' ]

doclines = [ x.strip() for x in __doc__.split('\n') if x ]

params.update( {
    'name': 'snmpsim',
    'version': open(os.path.join('snmpsim', '__init__.py')).read().split('\'')[1],
    'description': doclines[0],
    'long_description': ' '.join(doclines[1:]),
    'maintainer': 'Ilya Etingof <ilya@glas.net>',
    'author': 'Ilya Etingof',
    'author_email': 'ilya@glas.net',
    'url': 'http://sourceforge.net/projects/snmpsim/',
    'license': 'BSD',
    'platforms': ['any'],
    'classifiers': [ x for x in classifiers.split('\n') if x ],
    'scripts': [ 'scripts/snmpsimd.py',
                 'scripts/snmprec.py',
                 'scripts/datafile.py',
                 'scripts/pcap2dev.py',
                 'scripts/mib2dev.py' ],
    'packages': [ 'snmpsim', 'snmpsim.grammar', 'snmpsim.record',
                  'snmpsim.record.search' ]
} )

# install stock variation modules as data_files
params['data_files'] = [
    ( 'snmpsim/' + 'variation', glob.glob(os.path.join('variation', '*.py')) )
]

# install sample .snmprec files as data_files
for x in os.walk('data'):
    params['data_files'].append(
        ( 'snmpsim/' + '/'.join(os.path.split(x[0])),
          glob.glob(os.path.join(x[0], '*.snmprec')) + \
          glob.glob(os.path.join(x[0], '*.snmpwalk')) + \
          glob.glob(os.path.join(x[0], '*.sapwalk')) )
    )

if 'py2exe' in sys.argv:
    import py2exe
    # fix executables
    params['console'] = params['scripts']
    del params['scripts']
    # pysnmp used by snmpsim dynamically loads some of its *.py files
    params['options'] = {
        'py2exe': {
            'includes': [
                'pysnmp.smi.mibs.*',
                'pysnmp.smi.mibs.instances.*',
                'pysnmp.entity.rfc3413.oneliner.*'
            ],
            'bundle_files': 1,
            'compressed': True
        }
    }

    params['zipfile'] = None

    del params['data_files']  # no need to store these in .exe

    # additional modules used by snmpsimd but not seen by py2exe
    for m in ('dbm', 'gdbm', 'dbhash', 'dumbdb',
              'shelve', 'random', 'math', 'bisect',
              'sqlite3', 'subprocess', 'redis'):
        try:
            __import__(m)
        except ImportError:
            continue
        else:
            params['options']['py2exe']['includes'].append(m)

    print("!!! Make sure your pysnmp/pyasn1 packages are NOT .egg'ed!!!")

setup(**params)
