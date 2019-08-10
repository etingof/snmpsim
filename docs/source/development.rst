
Future features
===============

.. toctree::
   :maxdepth: 2

We are thinking of further SNMP Simulator development in these particular
areas:

SNMP credentials via variation modules
--------------------------------------

Let variation modules configuring custom SNMPv1/v2c community names and
SNMPv3 context names. That would be the alternative way to address simulation
data.

Complete SNMP table simulation
------------------------------

Simulating SNMP table: while the latest Simulator release supports
writable OIDs and SQL backend (which also allows for writable OIDs with
potentially complex logic triggered by their access), we think a lightweight
variation module readily implementing a RowStatus-driven SNMP table would
also be handy. Users of that module would invoke it from their *.snmprec*
file for an OID subtree serving their SNMP table. The module would
accept basic configuration parameters such as: table columns OIDs and types,
valid index ranges, default initialization parameters.

Render simulation data from templates
-------------------------------------

Allow rendering simulation data from a `template <http://jinja.pocoo.org/>`_
based on user-supplied variables possibly taken from SNMP query, process and
host contexts.

SNMP notifications simulation
-----------------------------

SNMP Notifications: current implementation can fully simulate SNMP Command
Generator operations. It would be nice to be able to record SNMP Notifications
coming from live SNMP Agents, store and replay them at configured rate and
possibly modified (variated) values.

Composable simulation data
--------------------------

Composable devices: the idea is to be able to compose simulated device from
specific MIBs the device implements.

Unordered OIDa
--------------

Re-work data files index implementation to allow unordered OIDs
and better performance on GETNEXT/GETBULK operations.

If you need one of these or some other feature - please open
a `feature request <https://github.com/etingof/snmpsim/issues/new>`_ at
GitHub or e-mail directly to *etingof@gmail.com* to discuss contractual
work possibilities.
