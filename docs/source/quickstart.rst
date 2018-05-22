
Quick start
===========

.. toctree::
   :maxdepth: 2

Installation
------------

SNMP Simulator is written in Python and depends on other Python libraries.
The easiest way to deploy SNMP Simulator is by downloading it from PyPI:

.. code-block:: bash

   $ virtualenv venv
   $ source venv/bin/activate
   $ pip install snmpsim

Run the simulator
-----------------

Once installed, invoke *snmpsimd.py* daemon and point it to a directory containing
simulation data:

.. code-block:: bash

   $ snmpsimd.py --data-dir=./data --agent-udpv4-endpoint=127.0.0.1:1024

Test the setup
--------------

Now you can query simulated agent(s) with Net-SNMP's command-line tools
which are usually shipped along with your operating system:

.. code-block:: bash

   $ snmpwalk -v2c -c public 127.0.0.1:1024 system
   SNMPv2-MIB::sysDescr.0 = STRING: Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686
   SNMPv2-MIB::sysObjectID.0 = OID: NET-SNMP-MIB::netSnmpAgentOIDs.10
   DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (126714301) 14 days, 15:59:03.01
   SNMPv2-MIB::sysContact.0 = STRING: SNMP Laboratories, info@snmplabs.com
   SNMPv2-MIB::sysName.0 = STRING: new system name
   SNMPv2-MIB::sysLocation.0 = STRING: San Francisco, California, United States
   SNMPv2-MIB::sysServices.0 = INTEGER: 72
   SNMPv2-MIB::sysORLastChange.0 = Timeticks: (126714455) 14 days, 15:59:04.55

Simulation data for each simulated SNMP agent is stored in simple plain-text file.
Each line in represents a single SNMP object in form of pipe-separated fields
*OID|TYPE|VALUE*.

.. code-block:: bash

   $ cat ./data/public.snmprec
   1.3.6.1.2.1.1.1.0|4|Linux 2.6.25.5-smp SMP Tue Jun 19 14:58:11 CDT 2007 i686
   1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.8072.3.2.10
   1.3.6.1.2.1.1.3.0|67|233425120
   1.3.6.1.2.1.2.2.1.6.2|4x|00127962f940
   1.3.6.1.2.1.4.22.1.3.2.192.21.54.7|64x|c3dafe61
   ...

Simulator uses the parameters (such as SNMP community name or SNMPv3 context
or IP address) of SNMP query to choose .snmprec file to respond with.

Simulate existing SNMP agent
----------------------------

Besides creating simulation data by hand, you can generate it from some
existing SNMP agent. Here we use publicly available SNMP Simulator instance
as a donor device:

.. code-block:: bash

   $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com --output-file=./data/public.snmprec
   SNMP version 2c, Community name: public
   Querying UDP/IPv4 agent at 195.218.195.228:161
   Agent response timeout: 3.00 secs, retries: 3
   Sending initial GETNEXT request for 1.3.6 (stop at <end-of-mib>)....
   OIDs dumped: 182, elapsed: 11.97 sec, rate: 7.00 OIDs/sec, errors: 0

Simulate from MIB
-----------------

Alternatively, you could build simulation data from a MIB file:

.. code-block:: bash

   $ mib2dev.py --output-file=./data/public.snmprec --mib-module=IF-MIB
   # MIB module: IF-MIB, from the beginning till the end
   # Starting table IF-MIB::ifTable (1.3.6.1.2.1.2.2)
   # Synthesizing row #1 of table 1.3.6.1.2.1.2.2.1
   ...
   # Finished table 1.3.6.1.2.1.2.2.1 (10 rows)
   # End of IF-MIB, 177 OID(s) dumped

You can even sniff network traffic on the wire recovering SNMP messages there
and building simulation data from it.

Besides static files, SNMP simulator can be configured to call its plugin modules
for simulation data. We ship plugins to interface SQL and noSQL databases, file-based
key-value stores and other sources of information.
