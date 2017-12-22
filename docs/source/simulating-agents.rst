
.. _simulating-agents:

Simulating SNMP Agents
======================

The *snmpsimd.py* program performs actual SNMP agent simulation based on the simulation
data provided.

.. _simulation-data-location:

Simulation data
---------------

SNMP agents simulation data ends up in :ref:`.snmprec <snmprec>` files. Once SNMP
request comes in, SNMP Simulator
:ref:`constructs .snmprec file path <addressing-simulation-data>` and tries to locate
it by searching through the following directories:

* ~/.snmpsim/data
* /usr/local/share/snmpsim/data
* {python-package-root}/data

On Windows search paths are:

* \Document and Settings\{user}\Application Data\SNMP Simulator\Data
* \Program Files\SNMP Simulator\Data
* {python-package-root}/data

These directories are searched in the specified order till the first match.
For example, a set up collection of *.snmprec* files would look like:

.. code-block:: bash

    $ cd /usr/local/share
    $ find snmpsim/data
    snmpsim/data
    snmpsim/data/public.snmprec
    snmpsim/data/mib2dev
    snmpsim/data/mib2dev/ip-mib.snmprec
    snmpsim/data/mib2dev/host-resources-mib.snmprec
    snmpsim/data/mib2dev/tcp-mib.snmprec
    snmpsim/data/foreignformats
    snmpsim/data/foreignformats/linux.snmpwalk
    snmpsim/data/foreignformats/winxp.sapwalk
    snmpsim/data/variation
    snmpsim/data/variation/subprocess.snmprec
    snmpsim/data/variation/virtualtable.snmprec
    snmpsim/data/recorded
    snmpsim/data/recorded/linksys-system.snmprec
    snmpsim/data/recorded/udp-endpoint-table-walk.snmprec
    ...

.. note::

    There're also a bunch of .dbm files created and maintained automatically
    in a temporary directory. These .dbm files are used by the Simulator
    for fast OID lookup in a data file.

.. _snmpsimd.py:

SNMP Simulator daemon
---------------------

The *snmpsimd.py* tool hosts multiple independent SNMP Command Responders.
It can run multiple SNMP engines exchanging data over multiple network interfaces.
Each SNMP engine instance can serve many independent sets of SNMP management
objects (MIBs) sourced from :ref:`local .snmprec files <snmprec>`
or :ref:`variation modules <simulation-with-variation-modules>`.

.. _multiple-listen-interfaces:

Multiple network interfaces
+++++++++++++++++++++++++++

SNMP Simulator daemon can listen at multiple local IP interfaces and/or UDP ports.
Just pass multiple *--agent-udpv4-endpoint* / *--agent-udpv6-endpoint* command
line parameters carrying addresses to listen on. Whenever you wish
Simulator to listen on thousands of local interfaces and/or ports,
use the *--agent-udpv4-endpoints-list* / *--agent-udpv6-endpoints-list*
options. These options expect to refer to a plain text file containing
newline-separated list of transport endpoints for Simulator to listen on.

.. code-block:: bash

    $ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1024 \
        --agent-udpv6-endpoint='[::1]:1161'
    Scanning "/home/user/.snmpsim/variation" directory for variation modules...
    no directory
    Scanning "/usr/local/share/snmpsim/variation" directory for variation modules...
      8 more modules found
    Initializing variation modules:
        notification...  OK
        sql...  FAILED: database type not specified
        numeric...  OK
        subprocess...  OK
        delay...  OK
        multiplex...  OK
        error...  OK
        writecache...  OK
    Scanning "/home/user/.snmpsim/data" directory for  *.snmpwalk, *.MVC,
    *.sapwalk, *.snmprec, *.dump data files... no directory
    Scanning "/usr/local/share/snmpsim/data" directory for  *.snmpwalk,
    *.MVC, *.sapwalk, *.snmprec, *.dump data files...
    ==================================================================
    Index /tmp/snmpsim/usr_local_share_snmpsim_data_public.dbm does not exist
    for data file data/public.snmprec
    Building index /tmp/snmpsim/usr_local_share_snmpsim_data_public.dbm for data
    file /usr/local/share/snmpsim/data/public.snmprec (open flags "n")......
    133 entries indexed
    Data file /usr/local/share/snmpsim/data/public.snmprec, dbhash-indexed, closed
    SNMPv1/2c community name: public
    SNMPv3 context name: 4c9184f37cff01bcdc32dc486ec36961
    -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    Index /tmp/snmpsim/usr_local_share_snmpsim_data_recorded_linksys-system.dbm
    does not exist for data file /usr/local/share/snmpsim/data/recorded/
    linksys-system.snmprec
    Building index /tmp/snmpsim/usr_local_share_snmpsim_data_recorded_linksys-
    system.dbm for data file /usr/local/share/snmpsim/data/recorded/linksys-
    system.snmprec (open flags "n")......6 entries indexed
    Data file /usr/local/share/snmpsim/data/recorded/linksys-system.snmprec,
    dbhash-indexed, closed
    SNMPv1/2c community name: recorded/linksys-system
    SNMPv3 context name: 1a764f7fd0e7b0bf98bada8fe723e488
    -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    ...
    ...
    ...
    SNMPv3 credentials:
    Username: simulator
    Authentication key: auctoritas
    Authentication protocol: MD5
    Encryption (privacy) key: privatus
    Encryption protocol: DES
    Listening at:
      UDP/IPv4 endpoint 127.0.0.1:1024, transport ID 1.3.6.1.6.1.1.0
      UDP/IPv6 endpoint ::1:1161, transport ID 1.3.6.1.2.1.100.1.2.0

.. note::

    An unprivileged port *1024* has been chosen in this example to avoid
    running *snmpsimd.py* process as root.

By this point you can run you favorite SNMP Manager to talk to either
of the two simulated devices through whatever transport you prefer.
For instance, to talk to simulated Linux box over SNMP v2 through
UDP over IPv4 run:

.. code-block:: bash

    $ snmpwalk -On -v2c -c recorded/linksys-system localhost:1161 1.3.6
    .1.3.6.1.2.1.1.1.0 = STRING: BEFSX41
    .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.3955.1.1
    .1.3.6.1.2.1.1.3.0 = Timeticks: (638239) 1:46:22.39
    .1.3.6.1.2.1.1.4.0 = STRING: Linksys
    .1.3.6.1.2.1.1.5.0 = STRING: isp-gw
    .1.3.6.1.2.1.1.6.0 = STRING: 4, Petersburger strasse, Berlin, Germany
    .1.3.6.1.2.1.1.8.0 = Timeticks: (4) 0:00:00.04
    .1.3.6.1.2.1.1.8.0 = No more variables left in this MIB View
    ...

To walk simulated 3com switch over SNMPv3 we'd run:

.. code-block:: bash

    $ snmpwalk -On -v3 -n recorded/linksys-system \
        -l authPriv -u simulator -A auctoritas -X privatus \
        localhost:1161 1.3.6
    .1.3.6.1.2.1.1.1.0 = STRING: BEFSX41
    .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.3955.1.1
    .1.3.6.1.2.1.1.3.0 = Timeticks: (638239) 1:46:22.39
    .1.3.6.1.2.1.1.4.0 = STRING: Linksys
    .1.3.6.1.2.1.1.5.0 = STRING: isp-gw
    .1.3.6.1.2.1.1.6.0 = STRING: 4, Petersburger strasse, Berlin, Germany
    .1.3.6.1.2.1.1.8.0 = Timeticks: (4) 0:00:00.04
    .1.3.6.1.2.1.1.8.0 = No more variables left in this MIB View
    ...

.. note::

    The *-n <snmp-context>* parameter passed to the *snmpwalk* tool addresses
    specific simulated device at SNMP Simulator daemon.

.. _multiple-usm-users:

Multiple USM users
++++++++++++++++++

It is also possible to configure many SNMPv3 (USM) users to Simulator. Each
set of *--v3-user*, *--v3-auth-key*, *--v3-priv-key* parameters adds one SNMPv3
user to Simulator.

There is no correlation between SNMPv3 users and simulated resources, all users
have the same view of the Simulator and the same access permissions. But
you can use SNMPv3 contextNames and/or transport endpoints for addressing
different data files e.g. simulated SNMP agents.

.. code-block:: bash

    $ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1  \
      --v3-user=wallace --v3-auth-key=testkey123 --v3-priv-key=testkey839 \
      --v3-user=gromit --v3-auth-key=testkey564 --v3-priv-key=testkey6534
    Scanning "/home/user/.snmpsim/variation" directory for variation modules...
    ...
    SNMPv3 EngineID 0x80004fb8056372617927fb76cc
    ------------------------------------------------------------------
    SNMPv3 USM SecurityName: wallace
    SNMPv3 USM authentication key: testkey123, authentication protocol: MD5
    SNMPv3 USM encryption (privacy) key: testkey839, encryption protocol: DES
    ------------------------------------------------------------------
    SNMPv3 USM SecurityName: gromit
    SNMPv3 USM authentication key: testkey564, authentication protocol: MD5
    SNMPv3 USM encryption (privacy) key: testkey6534, encryption protocol: DES
    Listening at UDP/IPv4 endpoint 127.0.0.1:161, transport ID 1.3.6.1.6.1.1.0
    ...

SNMP simulator supports many SNMPv3 authentication and encryption algorithms. For
each user you can configure any authentication and any encryption (privacy)
algorithm.

.. _auth-algos:

The following authentication algorithms are currently supported (via
*--v3-auth-proto=<ID>* option):

+--------+----------------+-------------+
| *ID*   | *Algorithm*    | *Reference* |
+--------+----------------+-------------+
| NONE   | -              | RFC3414     |
+--------+----------------+-------------+
| MD5    | HMAC MD5       | RFC3414     |
+--------+----------------+-------------+
| SHA    | HMAC SHA-1 128 | RFC3414     |
+--------+----------------+-------------+
| SHA224 | HMAC SHA-2 224 | RFC7860     |
+--------+----------------+-------------+
| SHA256 | HMAC SHA-2 256 | RFC7860     |
+--------+----------------+-------------+
| SHA384 | HMAC SHA-2 384 | RFC7860     |
+--------+----------------+-------------+
| SHA512 | HMAC SHA-2 512 | RFC7860     |
+--------+----------------+-------------+

.. _priv-algos:

The following privacy (encryption) algorithms are currently supported (via
*--v3-priv-proto=<ID>* option):

+------------+------------------------+----------------------+
| *ID*       | *Algorithm*            | *Reference*          |
+------------+------------------------+----------------------+
| NONE       | -                      | RFC3414              |
+------------+------------------------+----------------------+
| DES        | DES                    | RFC3414              |
+------------+------------------------+----------------------+
| AES        | AES CFB 128            | RFC3826              |
+------------+------------------------+----------------------+
| AES192     | AES CFB 192            | RFC Draft            |
+------------+------------------------+----------------------+
| AES256     | AES CFB 256            | RFC Draft            |
+------------+------------------------+----------------------+
| AES192BLMT | AES CFB 192 Blumenthal | RFC Draft            |
+------------+------------------------+----------------------+
| AES256BLMT | AES CFB 256 Blumenthal | RFC Draft            |
+------------+------------------------+----------------------+
| 3DES       | Triple DES EDE         | RFC Draft            |
+------------+------------------------+----------------------+

.. note::

    The AES192, AES256 and 3DES are implemented based on
    `Blumenthal <http://tools.ietf.org/html/draft-blumenthal-aes-usm-04>`_ and
    `Reeder <https://tools.ietf.org/html/draft-reeder-snmpv3-usm-3desede-00>`_
    draft RFCs.

Another configurable parameter is SNMPv3 snmpEngineId value. It's normally
automatically generated but can also be configured through
command line.

.. code-block:: bash

    $ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1 --v3-engine-id=010203040505060809
    Scanning "/home/user/.snmpsim/variation" directory for variation modules...
    ...
    SNMPv3 EngineID 0x010203040505060809
    ------------------------------------------------------------------
    SNMPv3 USM SecurityName: simulator
    SNMPv3 USM authentication key: auctoritas, authentication protocol: MD5
    SNMPv3 USM encryption (privacy) key: privatus, encryption protocol: DES
    Listening at UDP/IPv4 endpoint 127.0.0.1:161, transport ID 1.3.6.1.6.1.1.0

.. note::

    The *SnmpEngineId* value has to follow
    `certain format <href="http://tools.ietf.org/html/rfc3411#section-5">`_.

.. _multiple-snmp-engine-ids:

Multiple SNMP engines
+++++++++++++++++++++

SNMP Simulator could run many independent SNMP engines all within
a single daemon process.  SNMP managers could address particular
SNMP Engine instance by querying it at a transport endpoint to which
SNMP Engine is bound. 

Each SNMP Engine will have its own set of USM users and could serve
its own *--data-dir* (or they can share a single directory).

The logic of configuring specific parameters to different SNMP engines
is to "scope" SNMP Engine parameters (like users, transports, data directory)
within its *--v3-engine-id* fragment of Simulator command-line sequence of
options.  For example:

.. code-block:: bash

    $ snmpsimd.py \
      --v3-engine-id=010203040505060809 \
      --v3-user=wallace --v3-auth-key=testkey123 \
      --agent-udpv4-endpoint=127.0.0.1:1161 \
      --v3-engine-id=090807060504030201 \
      --v3-user=gromit --v3-auth-key=testkey564 \
      --agent-udpv4-endpoint=127.0.0.1:1162
    Scanning "/home/user/.snmpsim/variation" directory for variation modules...
    ...
    SNMPv3 EngineID: 0x010203040505060809
    ------------------------------------------------------------------
    SNMPv3 USM SecurityName: wallace
    SNMPv3 USM authentication key: testkey123, authentication protocol: MD5
    Listening at UDP/IPv4 endpoint 127.0.0.1:1161, transport ID 1.3.6.1.6.1.1.0
    ...
    SNMPv3 EngineID: 0x090807060504030201
    ------------------------------------------------------------------
    SNMPv3 USM SecurityName: gromit
    SNMPv3 USM authentication key: testkey564, authentication protocol: MD5
    Listening at UDP/IPv4 endpoint 127.0.0.1:1162, transport ID 1.3.6.1.6.1.1.1

Likewise, to make particular SNMP Engine working with specific data directory,
another, more specific, *--data-dir* option could be passed after the
*--v3-engine-id* option.

.. _running-options:

Invocation options
++++++++++++++++++

To make Simulator listening on SNMP-standard UDP port 161 on a UNIX system,
you have to invoke it as root but in the same time have to specify some
non-privileged UNIX user and group to switch into upon port allocation:

.. code-block:: bash

    # snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:161 \
        --process-user=simulator --process-group=simulator

On UNIX systems Simulator can be run as a daemon. Make sure to re-direct
its console output into syslog:

.. code-block:: bash

    # snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:161 \
        --process-user=simulator --process-group=simulator \
        --daemonize --logging-method=syslog:local1:debug

.. _logging-options:

Logging options
+++++++++++++++

Most of the scripts shipped with the SNMP Simulator package can log to a remote syslog
server over TCP or UDP:

.. code-block:: bash

    # snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:161 \
        --process-user=simulator --process-group=simulator \
        --daemonize --logging-method=syslog:local1:debug:192.168.1.1:514:udp

Finally, Simulator can simply log to a local log file:

.. code-block:: bash

    # snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:161 \
        --process-user=simulator --process-group=simulator \
        --daemonize --logging-method=file:/var/log/snmpsimd.log

