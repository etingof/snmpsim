
SNMP Agent Simulator
====================

SNMP Simulator tool can simulate many thousands of different
SNMP speaking devices on a network. It is primarily being used for testing
and development purposes.

The software is free, open source and immediately available to anyone for
whatever purpose.

How to use SNMP Simulator
-------------------------

Try the fast lane if you are fluent with network management matters.

.. toctree::
   :maxdepth: 2

   /quickstart

SNMP Simulator suite
--------------------

Detailed documentation explaining the entire work flow and SNMP simulator
tool set.

For larger-scale, automated deployments REST API based
`control plane <http://snmplabs.com/snmpsim-control-plane>`_ can be used for
centralized management and monitoring purposes.

.. toctree::
   :maxdepth: 2

   /documentation/contents.rst

Source code & Changelog
-----------------------

Project source code is hosted at `GitHub <https://github.com/etingof/snmpsim>`_.
Everyone is welcome to fork and contribute back!

We maintain a detailed log of changes:

.. toctree::
   :maxdepth: 1

   /changelog

Download
--------

The easiest way to download and install SNMP simulator is to `pip install` the latest
version from PyPI:

.. code-block:: bash

   $ virtualenv venv
   $ source venv/bin/activate
   $ pip install snmpsim

Alternatively, you can `download <https://github.com/etingof/snmpsim/releases>`_
the latest release from GitHub or `PyPI <https://pypi.org/project/snmpsim/>`_.

License
-------

The SNMP Simulator software is distributed under 2-clause BSD license

.. toctree::
   :maxdepth: 1

   /license

Development
-----------

Our development plans and new features we consider for eventual implementation
are tracked on the future features page.

.. toctree::
   :maxdepth: 2

   /development

Contact
-------

In case of questions or troubles using SNMP Simulator, please open up an
`issue <https://github.com/etingof/snmpsim/issues>`_ at GitHub or ask at
`Stack Overflow <http://stackoverflow.com/questions/tagged/snmpsim>`_ .
You can also try browsing the mailing list
`archives <http://lists.sourceforge.net/mailman/listinfo/snmpsim-users>`_.
