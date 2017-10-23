
SNMP Agent Simulator
====================

.. toctree::
   :maxdepth: 2

SNMP Simulator tool can simulate many thousands of different
SNMP speaking devices on a network. It is primarily used for testing
and development purposes.

It is free, open source and immediately available to anyone for whatever
purpose free of charge.

How to use SNMP Simulator
-------------------------

Try the fast lane if you are fluent with network management matters.

.. toctree::
   :maxdepth: 2

   /quickstart

Documentation
-------------

.. toctree::
   :maxdepth: 2

   /simulating-agents
   /managing-simulation-data
   /addressing-agents
   /simulation-with-variation-modules
   /building-simulation-data
   /recording-with-variation-modules
   /tips-and-tricks

Source code & Changelog
-----------------------

Project source code is hosted at `GitHub <https://github.com/etingof/snmpsim>`_.
Everyone is welcome to fork and contribute back!

We maintain detailed :doc:`log of changes </changelog>` to our software.

Download
--------

The easiest way to download and install SNMP simulator is to `pip install` the latest
version from PyPI:

.. code-block:: bash

   $ virtualenv venv
   $ source venv/bin/activate
   $ pip install snmpsim

Alternatively, you can download the latest release from `GitHub <https://github.com/etingof/snmpsim/releases>`_
or `PyPI <https://pypi.python.org/pypi/snmpsim>`_.

License
-------

The SNMP Simulator software is distributed under 2-clause :doc:`BSD license </license>`.

Development
-----------

Our development plans and new features we consider for eventual implementation
are tracked on the :doc:`future features </development>` page.

Free simulation service
-----------------------

We setup :doc:`publicly available SNMP Simulator </public-snmp-agent-simulator>`
instance at `Digital Ocean <https://cloud.digitalocean.com/>`_ cloud to serve
SNMP simulation services to you - our fellow SNMP developers
and testers. The service is hosted in the U.S. (west coast) and should
be available to everyone free of charge.

If you are considering signing up with Digital Ocean for their
hosting services, `the voucher <https://m.do.co/c/debefe816df4>`_
will get you $10 credit and that would benefit our service hosting as well. ;-)

Contact
-------

In case of questions or troubles using SNMP Simulator, please open up an
`issue <https://github.com/etingof/snmpsim/issues>`_ at GitHub or ask at
`Stack Overflow <http://stackoverflow.com/questions/tagged/snmpsim>`_ .
You can also try browsing the mailing list
`archives <http://lists.sourceforge.net/mailman/listinfo/snmpsim-users>`_.
