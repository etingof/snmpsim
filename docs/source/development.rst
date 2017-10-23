
Future features
===============

We are thinking of further SNMP Simulator development in these particular
areas:

* Re-work data files indices implementation to allow unordered OIDs
  and better performance on GETNEXT/GETBULK operations.

* Let variation modules configuring custom SNMPv1/v2c community names and
  SNMPv3 context names. That would be the alternative way to address simulation
  data.

* Simulating SNMP table: while the latest Simulator release supports
  writable OIDs and SQL backend (which also allows for writable OIDs with
  potentially complex logic triggered by their access), we think a lightweight
  variation module readily implementing a RowStatus-driven SNMP table would
  also be handy. Users of that module would invoke it from their *.snmprec*
  file for an OID subtree serving their SNMP table. The module would
  accept basic configuration parameters such as: table columns OIDs and types,
  valid index ranges, default initialization parameters.

* Allow rendering simulation data from a `template <http://jinja.pocoo.org/>`_
  based on user-supplied variables possibly taken from SNMP query, process and
  host contexts.

* SNMP Notifications: current implementation can fully simulate SNMP Command
  Generator operations. It would be nice to be able to record SNMP Notifications
  coming from live SNMP Agents, store and replay them at configured rate and
  possibly modified (variated) values.

* Implement REST API to *snmpsimd.py* to let user record and replay snapshots through
  a web browser or in-house automation scripts.

* Composable devices: the idea is to be able to compose simulated device from
  specific MIBs the device implements.

If you need one of these or some other feature - please open
a `feature request <https://github.com/etingof/snmpsim/issues/new>`_ at
GitHub or e-mail directly to *etingof@gmail.com* to discuss contractual
work possibilities.
