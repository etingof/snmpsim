#!/usr/bin/env python
import sys
import glob

def howto_install_setuptools():
    print """Error: You need setuptools Python package!

It's very easy to install it, just type (as root on Linux):
   wget http://peak.telecommunity.com/dist/ez_setup.py
   python ez_setup.py
"""

try:
    from setuptools import setup
    params = {
        'install_requires': [ 'pysnmp' ],
        'zip_safe': True
        }
except ImportError:
    for arg in sys.argv:
        if "egg" in arg:
            howto_install_setuptools()
            sys.exit(1)
    from distutils.core import setup
    if sys.version_info > (2, 2):
        params = {
            'requires': [ 'pysnmp' ]
            }
    else:
        params = {}

params.update( {
    'name': "snmpsim",
    'version': "0.0.10",
    'description': "SNMP devices simulator",
    'author': "Ilya Etingof",
    'author_email': "ilya@glas.net ",
    'url': "http://sourceforge.net/projects/snmpsim/",
    'scripts': [ 'snmpsimd.py', 'snmprec.py' ],
    'license': "BSD"
  } )

if "py2exe" in sys.argv:
    import py2exe
    # fix executables
    params['console'] = params['scripts']
    del params['scripts']

apply(setup, (), params)
