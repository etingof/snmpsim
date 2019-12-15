
.. _addressing-simulation-data:

Addressing SNMP agents
======================

Sometimes SNMP managers can't easily change community name to address
particular simulated device instance as mention in the previous section.
Or it may be useful to present the same simulated device to different
SNMP managers differently.

.. _lite-mode-variation:

Lite mode
---------

When running lite command responder, SNMP Simulator is not using SNMPv3
framework. That implies that SNMPv3 infrastructure can't be used for agent
addressing. In this mode, only SNMP v1 and v2c versions can be handled. The
main reason for this lite/legacy mode support is higher performance.

In lite mode, SNMP Simulator attempts to find a *.snmprec* file to
fulfill the request by probing files by paths constructed from pieces of
SNMPv1/v2c request data. Path construction occurs by these rules and
in this order:

1. *self / <community> / <transport-ID> / <source-address>* .snmprec
2. *self / <community> / <transport-ID>* .snmprec
3. *self / <community>* .snmprec
4. *self* .snmprec

The *self* component is just a constant which conceptually refers to the SNMP
engine serving current request.

One of the use-cases is to serve requests with empty SNMP community name.

In other words, SNMP Simulator first tries to take community name,
destination and source addresses into account. If that does not match
any existing file, the next probe would use community name and
destination address. The last resort is to probe files by just
community name, as described in previous chapters.

Transport ID is an OID that also identifies local transport endpoint (e.g.
protocol, local address and port Simulator is listening on). It is reported
by the Simulator on startup for each endpoint it is listening on.

.. code-block:: bash

    $ snmpsim-command-responder-lite \
        --agent-udpv4-endpoint=127.0.0.1:1024 \
        --agent-udpv6-endpoint='[::1]:1161'
    ...
    Listening at:
      UDP/IPv4 endpoint 127.0.0.1:1024, transport ID 1.3.6.1.6.1.1.0
      UDP/IPv6 endpoint ::1:1161, transport ID 1.3.6.1.2.1.100.1.2.0

When mapping source-address into a file, the following transformation
rules apply:

* UDP/IPv4:
    192.168.1.1 remains 192.168.1.1

* UDP/IPv6:
    fe80::12e:410f:40d1:2d13 becomes fe80__12e_410f_40d1_2d13

For example, to make Simulator reporting from particular file to
a Manager at 192.168.1.10 whenever community name "public" is used and
queries are sent to Simulator over UDP/IPv4 to 192.168.1.1 interface
(which is reported by Simulator under transport ID 1.3.6.1.6.1.1.0),
device file *self/public/1.3.6.1.6.1.1.0/192.168.1.10.snmprec* would be used
for building responses.

.. _full-mode-variation:

SNMPv3 mode
-----------

When using full Simulator, SNMPv3 framework is used and all SNMP versions (1, 2c, 3)
can be handled.

The same filesystem mapping rules apply to SNMP community name, but also to SNMPv3
context name. The path to .snmprec file for fulfilling response is probed at these
locations in the following order:

1. *context-engine-id / context-name / transport-ID / source-address* .snmprec
2. *context-engine-id / context-name / transport-ID* .snmprec
3. *context-engine-id / context-name* .snmprec
4. *context-engine-id* .snmprec

The *context-engine-id* component is taken from SNMP Context Engine ID field
of the SNMP command request. If it happens to be equal to local SNMP engine ID
value, then the constant literal *self* will be looked up on the file system
instead. Conceptually, *self* refers to the SNMP engine serving current request.

One of the side-effects of supporting *context-engine-id* is to serve requests
with empty SNMP context/community name  (i.e. *self.snmprec*).

For example, to make Simulator reporting from particular file to
a Manager at 192.168.1.10 whenever context-name is an empty string and
queries are sent to Simulator over UDP/IPv4 to 192.168.1.1 interface
(which is reported by Simulator under transport ID 1.3.6.1.6.1.1.0),
device file *self/1.3.6.1.6.1.1.0/192.168.1.10.snmprec* would be used
for building responses.

.. _sharing-snmprec-files:

Sharing .snmprec files
----------------------

If a symbolic link is used as a data file, it would serve as an
alternative CommunityName/ContextName for the Managed Objects collection
read from the snapshot file being pointed to:

.. code-block:: bash

    $ ls -l public.snmprec
    -rw-r--r-- 1 root users 8036 Mar 12 23:26 public.snmprec
    $ ln -s public.snmprec private.snmprec
    $ ls -l private.snmprec
    lrwxrwxrwx 1 root users 14 Apr  5 20:58 private.snmprec -> public.snmprec

Shared device files are mentioned explicitly on *snmpsim-command-responder*
startup:

.. code-block:: bash

    $ snmpsim-command-responder --agent-udpv4-endpoint=127.0.0.1:1161
    Scanning "/home/root/.snmpsim/variation" directory for variation modules...
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
    Scanning "/usr/local/share/snmpsim/data" directory for  *.snmpwalk, *.MVC,
    *.sapwalk, *.snmprec, *.dump data files...
    ==================================================================
    Data file /usr/local/share/snmpsim/data/public.snmprec, dbhash-indexed, closed
    SNMPv1/2c community name: public
    SNMPv3 context name: 4c9184f37cff01bcdc32dc486ec36961
    -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    Shared data file data/public.snmprec, dbhash-indexed, closed
    SNMPv1/2c community name: private
    SNMPv3 context name: 2c17c6393771ee3048ae34d6b380c5ec
    -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    ...

    SNMPv3 credentials:
    Username: simulator
    Authentication key: auctoritas
    Authentication protocol: MD5
    Encryption (privacy) key: privatus
    Encryption protocol: DES

    Listening at:
      UDP/IPv4 endpoint 127.0.0.1:1161, transport ID 1.3.6.1.6.1.1.0

Now Managers can then use different credentials to access and modify the
same set of Managed Objects.

.. code-block:: bash

    $ snmpwalk -On -v2c -c public localhost:1161 1.3.6
    .1.3.6.1.2.1.1.1.0 = STRING: Device description
    .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.34547
    .1.3.6.1.2.1.1.3.0 = Timeticks: (78171676) 9 days, 1:08:36.76
    .1.3.6.1.2.1.1.4.0 = STRING: The Owner
    .1.3.6.1.2.1.1.5.0 = STRING: DEVICE-192.168.1.1
    .1.3.6.1.2.1.1.6.0 = STRING: TheCloud
    .1.3.6.1.2.1.1.7.0 = INTEGER: 72
    ...

    $ snmpwalk -On -v2c -c private localhost:1161 1.3.6
    .1.3.6.1.2.1.1.1.0 = STRING: Device description
    .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.34547
    .1.3.6.1.2.1.1.3.0 = Timeticks: (78171676) 9 days, 1:08:36.76
    .1.3.6.1.2.1.1.4.0 = STRING: The Owner
    .1.3.6.1.2.1.1.5.0 = STRING: DEVICE-192.168.1.1
    .1.3.6.1.2.1.1.6.0 = STRING: TheCloud
    .1.3.6.1.2.1.1.7.0 = INTEGER: 72
    ...

Obviously, *snmpwalk* output is exactly the same for different community names
being used.
