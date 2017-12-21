
.. _snmp-simulation-service:

SNMP simulation service
=======================

Free and publicly available SNMP simulation service is set up at *demo.snmplabs.com*.

.. _simulated-snmp-engines:

SNMP engines
------------

There are four independent SNMP engines configured at different UDP ports:

+--------------------------------+-------------------+----------------+
| **SNMP Engine ID**             | **Hostname**      | **UDP port**   |
+--------------------------------+-------------------+----------------+
| 0x80004fb805636c6f75644dab22cc | demo.snmplabs.com | 161 (standard) |
+--------------------------------+-------------------+----------------+
| 0x80004fb805636c6f75644dab22cd | demo.snmplabs.com | 1161           |
+--------------------------------+-------------------+----------------+
| 0x80004fb805636c6f75644dab22ce | demo.snmplabs.com | 2161           |
+--------------------------------+-------------------+----------------+
| 0x80004fb805636c6f75644dab22cf | demo.snmplabs.com | 3161           |
+--------------------------------+-------------------+----------------+

.. note::

   The simulation service is implemented by two independent UNIX processes.
   One process runs the first SNMP engine (*0x80004fb805636c6f75644dab22cc*)
   while the rest of SNMP engines in the table above are all local to the
   second SNMP simulator process.

.. _simulated-community-names:

SNMP community names
--------------------

Each of the :ref:`SNMP engines <simulated-snmp-engines>` supports a
:ref:`bunch of SNMP community names <simulated-data>` to address distinct
simulated SNMP agent.

To start with, the conventional **public** and **private** SNMP community names
are available as well.

.. _simulated-usm-users:

SNMPv3 USM users
----------------

Each :ref:`SNMP engines <simulated-snmp-engines>` has the following USM users
configured to it. We support many SNMPv3 encryption protocol combinations indexed
by USM user name.

+------------------------+---------------------------+----------------------+-------------------------+------------------+
| USM Security Name      | Authentication protocol   | Authentication key   | Encryption protocol     | Encryption key   |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-none-none          | -                         | -                    | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-none           | MD5                       | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-des            | MD5                       | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-3des           | MD5                       | authkey1             | Triple DES              | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes            | MD5                       | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes128         | MD5                       | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes192         | MD5                       | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes192-blmt    | MD5                       | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes256         | MD5                       | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-md5-aes256-blmt    | MD5                       | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-none           | SHA1 (96/160bit)          | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-des            | SHA1 (96/160bit)          | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-3des           | SHA1 (96/160bit)          | authkey1             | Triple DES              | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes            | SHA1 (96/160bit)          | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes128         | SHA1 (96/160bit)          | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes192         | SHA1 (96/160bit)          | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes192-blmt    | SHA1 (96/160bit)          | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes256         | SHA1 (96/160bit)          | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha-aes256-blmt    | SHA1 (96/160bit)          | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-none        | SHA2 (128/224bit)         | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-des         | SHA2 (128/224bit)         | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-3des        | SHA2 (128/224bit)         | authkey1             | Triple DES              | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes         | SHA2 (128/224bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes128      | SHA2 (128/224bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes192      | SHA2 (128/224bit)         | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes192-blmt | SHA2 (128/224bit)         | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes256      | SHA2 (128/224bit)         | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha224-aes256-blmt | SHA2 (128/224bit)         | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-none        | SHA2 (192/256bit)         | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-des         | SHA2 (192/256bit)         | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-3des        | SHA2 (192/256bit)         | authkey1             | Triple DES              | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes         | SHA2 (192/256bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes128      | SHA2 (192/256bit)         | authkey1             | AES (192bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes192      | SHA2 (192/256bit)         | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes192-blmt | SHA2 (192/256bit)         | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes256      | SHA2 (192/256bit)         | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha256-aes256-blmt | SHA2 (192/256bit)         | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-none        | SHA2 (256/384bit)         | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-des         | SHA2 (256/384bit)         | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes         | SHA2 (256/384bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes128      | SHA2 (256/384bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes192      | SHA2 (256/384bit)         | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes192-blmt | SHA2 (256/384bit)         | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes256      | SHA2 (256/384bit)         | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha384-aes256-blmt | SHA2 (256/384bit)         | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-none        | SHA2 (384/512bit)         | authkey1             | -                       | -                |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-des         | SHA2 (384/512bit)         | authkey1             | DES                     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-3des        | SHA2 (384/512bit)         | authkey1             | Triple DES              | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-aes         | SHA2 (384/512bit)         | authkey1             | AES (128bit)            | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-aes192      | SHA2 (384/512bit)         | authkey1             | AES Reeder (192bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-aes192-blmt | SHA2 (384/512bit)         | authkey1             | AES Blumenthal (192bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-aes256      | SHA2 (384/512bit)         | authkey1             | AES Reeder (256bit)     | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+
| usr-sha512-aes256-blmt | SHA2 (384/512bit)         | authkey1             | AES Blumenthal (256bit) | privkey1         |
+------------------------+---------------------------+----------------------+-------------------------+------------------+

.. note::

   The *Triple DES* authentication algorithm is implemented according to
   `draft-reeder-snmpv3-usm-3desede-00 <https://tools.ietf.org/html/draft-reeder-snmpv3-usm-3desede-00#section-5>`_.
   The AES-based privacy algorithms with key size 192bit+ are implemented along the lines of
   `draft-blumenthal-aes-usm-04 <https://tools.ietf.org/html/draft-blumenthal-aes-usm-04#section-3>`_)
   with either Reeder or Blumenthal  key localization.

.. _simulated-data:

Simulation data
---------------

Each of the :ref:`SNMP engines <simulated-snmp-engines>` simulate multiple SNMP agents addressable
by the following SNMP query parameters:

+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| **SNMP agent**                                                     | **SNMP community**                 | **SNMP context name**              |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| Dynamically variated, writable SNMP Agent                          | public                             | -                                  |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| Static snapshot of a Linux host                                    | recorded/linux-full-walk           | a172334d7d97871b72241397f713fa12   |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| Static snapshot of a Windows XP PC                                 | foreignformats/winxp2              | da761cfc8c94d3aceef4f60f049105ba   |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| Series of static snapshots of live IF-MIB::interfaces              | variation/multiplex                | 1016117d6836664ee15b9b2af5642c3c   |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+
| Simulated IF-MIB::interfaces table with ever increasing counters   | variation/virtualtable             | 329a935947144eb87ad0cdc5e08927b1   |
+--------------------------------------------------------------------+------------------------------------+------------------------------------+

TRAP sink
---------

Besides simulated SNMP Agents we are also running a multilingual
SNMP Notification Receiver. It will consume and optionally acknowledge
SNMP TRAP/INFORM messages you might send to *demo.snmplabs.com:162*.

SNMPv1/v2c community name is **public**. Configured SNMPv3 USM users
and keys are :ref:`the same <simulated-usm-users>` as for SNMP agents.

Keep in mind that our SNMPv3 TRAP receiving service is configured for
authoritative SNMP engine ID **8000000001020304**. You would have to
explicitly configure it to your SNMP notification originator.

Obviously, you won't get any response from your TRAP messages, however
you will get an acknowledgement for the INFORM packets you send us.

Examples
--------

To query simulated live *IF-MIB::interfaces* over SNMPv2c use the
following command:

.. code-block:: bash

    $ snmpwalk -v2c -c variation/virtualtable demo.snmplabs.com IF-MIB::interfaces

Some of the simulated objects are configured writable so you can experiment
with SNMP SET:

.. code-block:: bash

    $ snmpwalk -v2c -c public demo.snmplabs.com system
    ...
    SNMPv2-MIB::sysORDescr.1 = STRING: Please modify me
    SNMPv2-MIB::sysORUpTime.1 = Timeticks: (1) 0:00:00.01
    $
    $ snmpset -v2c -c private demo.snmplabs.com \
      SNMPv2-MIB::sysORDescr.1 = 'Here is my new note'
    SNMPv2-MIB::sysORDescr.1 = STRING: Here is my new note
    $ snmpset -v2c -c private demo.snmplabs.com \
      SNMPv2-MIB::sysORUpTime.1 = 321
    SNMPv2-MIB::sysORUpTime.1 = Timeticks: (321) 0:00:03.21
    $ snmpwalk -v2c -c public demo.snmplabs.com system
    ...
    SNMPv2-MIB::sysORDescr.1 = STRING: Here is my new note
    SNMPv2-MIB::sysORUpTime.1 = Timeticks: (321) 0:00:03.21

The above table is not complete, you could always figure out the most
actual list of simulated SNMP Agents by fetching relevant SNMP table
off the SNMP Simulator:

.. code-block:: bash

    $ snmpwalk -v2c -c index demo.snmplabs.com 1.3.6
    SNMPv2-SMI::enterprises.20408.999.1.1.1 = STRING: "/usr/snmpsim/data/1.3.6.1.6.1.1.0/127.0.0.1.snmprec"
    SNMPv2-SMI::enterprises.20408.999.1.1.2 = STRING: "/usr/snmpsim/data/public.snmprec"
    SNMPv2-SMI::enterprises.20408.999.1.1.3 = STRING: "/usr/snmpsim/data/foreignformats/winxp2.sapwalk"
    ...

Example SNMPv3 TRAP would look like this:

.. code-block:: bash

    $ snmptrap -v3 -l authPriv -u usr-md5-des -A authkey1 -X privkey1 \
      -e 8000000001020304 demo.snmplabs.com \
      12345 1.3.6.1.4.1.20408.4.1.1.2 1.3.6.1.2.1.1.1.0 s hello

Normal SNMP engine ID discovery would work for SNMP INFORMs, hence
securityEngineId should not be used:

.. code-block:: bash

    $ snmpinform -v3 -l authPriv -u usr-md5-des -A authkey1 -X privkey1 \
      demo.snmplabs.com 12345 \
      1.3.6.1.4.1.20408.4.1.1.2 1.3.6.1.2.1.1.1.0 s hello

Be advised that this is a free, experimental service provided as-is without
any guarantees on its reliability and correctness. Its use is generally covered
by SNMP Simulator :doc:`/license`.

In case of any troubles or suggestions, please
`open up a <https://github.com/etingof/snmpsim/issues/new>`_ GitHub issue.
