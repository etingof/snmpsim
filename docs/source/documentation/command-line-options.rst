
Command-line options
====================

.. toctree::
   :maxdepth: 2

The SNMP Simulator suite consists of a handful of command-line tools that
take command-line options.

Common options
--------------

**--debug-snmp**
++++++++++++++++

The *--debug-snmp* option makes the daemon emitting detailed log of SNMP
protocol related debugging. Debugging can be enabled for all or for just
some of the SNMP engine subsystems by adding their names to the
*--debug-snmp* option.

Recognized SNMP debugging options include:

* *io* -- report raw network traffic
* *msgproc* -- report SNMP message processing
* *secmod* -- report SNMP security module operations
* *mibbuild* -- report on MIB loading and processing
* *mibinstrum* -- report agent MIB operatrions
* *acl* -- report MIB access access control operations
* *proxy* -- report on SNMP version translation operations
* *app* -- application-specific debugging
* *all* -- enable full SNMP debugging

SNMP debugging is fully disabled by default.

**--debug-asn1**
++++++++++++++++

SNMP is backed by the
`ASN.1 <https://en.wikipedia.org/wiki/Abstract_Syntax_Notation_One>`_
for data representation and serialization purposes. The *--debug-asn1* option
makes the tools emitting detailed log of ASN.1 data de/serialization. Debugging
can be enabled for either encoder or decoder, or for everything ASN.1 related
by adding their names to the *--debug-asn1* option.

Recognized ASN.1 debugging options include:

* *encoder* -- debug data serialization
* *decoder* -- debug data deserialization
* *all* -- enable full ASN.1 debugging

ASN.1 debugging is fully disabled by default.

**--logging-method**
++++++++++++++++++++

Some of the SNMP Simulator tools can log using one of the following methods.
The default is *stderr*.

**--logging-method=syslog**
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *syslog* logging method requires the following sub-options:

.. code-block:: bash

    --logging-method=syslog:facility[:address[:port:[tcp|udp]]]]

Where:

* *facility* -- one of the recognized syslog service
  `facilities <https://en.wikipedia.org/wiki/Syslog#Facility>`_
* *address* -- can be either an absolute path to a local socket or network
  address where syslog service is listening (optional)
* *port* -- if network address of the syslog service is used for *address*,
  *port* be a TCP or UDP port number (optional)
* *tcp* or *udp* -- TCP (stream) or UDP (datagram) protocol to use for
  syslog service communication (optional)

**--logging-method=file**
~~~~~~~~~~~~~~~~~~~~~~~~~

The *file* logging method redirects daemon logging into a local file. The
log file could be made automatically rotated based on time or size criteria.

The following sub-options are supported:

.. code-block:: bash

    --logging-method=file:path[:criterion]

Where:

* *path* -- path to a log file
* *criterion* -- should consist of a number followed by one of the specifiers:

  - *k* -- rotate when file size exceeds N kilobytes
  - *m* -- rotate when file size exceeds N megabytes
  - *g* -- rotate when file size exceeds N gigabytes
  - *S* -- rotate when file age exceeds N seconds
  - *M* -- rotate when file age exceeds N minutes
  - *H* -- rotate when file age exceeds N hours
  - *D* -- rotate when file age exceeds N days

**--logging-method=stdout/stderr**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When *stdout* or *stderr* logging methods are used, daemon log messages are
directed to either process standard output or standard error stream.

**--logging-method=null**
~~~~~~~~~~~~~~~~~~~~~~~~~

The *null* logging method completely inhibits all daemon logging.

**--log-level**
+++++++++++++++

The *--log-level* option limits the minimum severity of the log messages
to actually log.

Recognized log levels are:

* *debug* -- log at all levels
* *info* - log informational and error messages only
* *error* - log error messages only

SNMP command responders
-----------------------

SNMP Simulator can be run as *snmpsim-command-responder* (full version) or
*snmpsim-command-responder-lite* (lightweight version). Both programs
take the following common command-line options.

Common command responders options
---------------------------------

The lightweight SNMP command responder implementation is limited to SNMP v1
and v2c protocol versions. Full SNMP command responder implementation supports
all SNMP versions.

The following options are respected by both SNMP command responder
applications.

**--daemonize**
+++++++++++++++

Unless *--daemonize* option is given, the daemon will remain an interactive
process. With the *--daemonize* option, the daemon will detach itself from
user terminal, close down standard I/O streams etc.

**--process-user** & **--process-group**
++++++++++++++++++++++++++++++++++++++++

It is generally safer to run daemons under a non-privileged user. However,
it may be necessary to, at least, start SNMP Simulator parts as root
to let the process bind to privileged ports (161/udp for SNMP by default).

In this case it may make sense to drop process privileges upon
initialization by becoming *--process-user* belonging to *--process-group*.

**--pid-file**
++++++++++++++

Especially when running in *--daemonize* mode, it might be handy to keep
track of UNIX process ID allocated to the running daemon. Primarily, this
can be used for killing or restarting the process.

The *--pid-file* option can be used to specify a disk file where daemon
would store its PID.

Default is not to create PID file.

**--cache-dir**
+++++++++++++++

Specifies path to directory for temporary indices used for fast simulation
data lookup. The indices for all .snmprec files will be built on process
start unless they already exist and not outdated.

Default is `$TEMPDIR/snmpsim`.

**--reporting-method**
++++++++++++++++++++++

SNMP command responder applications can collect and periodically emit
various activity metrics.

The default is *null* that disables activity collection and reporting.

**--reporting-method=fulljson**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *fulljson* activity reporting method collects and reports highly
detailed activity metrics. It may become expensive when simulating thousands
of transport endpoints or SNMP agents.

The *fulljson* reporting method supports the following sub-options:

.. code-block:: bash

    --reporting-method=fulljson:reports-dir

Where:

* *reports-dir* -- location on the filesystem where this reporting module
  should dump collected metrics.

**--reporting-method=minimaljson**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *minimaljson* activity reporting method collects and reports minimal
activity metrics. Essentially, it collapses individual metrics for transport
endpoints, agents, data files into one.

The *minimaljson* reporting method supports the following sub-options:

.. code-block:: bash

    --reporting-method=minimaljson:reports-dir

Where:

* *reports-dir* -- location on the filesystem where this reporting module
  should dump collected metrics.

**--variation-modules-dir**
+++++++++++++++++++++++++++

Specifies path to the directory where SNMP simulator should look for variation
modules. All modules found there will be imported and initialized for
further use from the .snmprec files.

Default search path is dependent on the platform. On Linux it is:

* `$HOME/.snmpsim/variation`
* `/usr/snmpsim/variation`
* `/usr/share/snmpsim/variation`
* `<program dir>/variation`

**--variation-module-options**
++++++++++++++++++++++++++++++

Some variation modules accept configuration options. These options could be
given in the form of `:`-separated positional arguments:

.. code-block:: bash

   --variation-module-options=<module[=alias][:args]

If the same variation module needs to be used with different set of
configuration parameters, one or more aliases could be created. Each instance
of the variation module could then be referenced from the .snmprec files
by alias.

Example:

.. code-block:: bash

    --variation-module-options=sql=mydb:dbtype:sqlite3,database:/tmp/snmpsim.db

**--force-index-rebuild**
+++++++++++++++++++++++++

Force rebuilding indices for all the .snmprec files regardless of their age and
status. With this option, the rebuild happens on every *snmpsim-command-responder*
process startup.

The default is off.

**--validate-data**
+++++++++++++++++++

Normally, SNMP simulator does not evaluate simulation values configured in the
.snmprec files (however it evaluates the OIDs when building look up indices).
With this option SNMP simulator will also evaluate simulation data on process
startup.

The default is off.

**--max-varbinds**
++++++++++++++++++

Maximum number of SNMP objects to serve in response to the *GETBULK* command
per each requested variable-binding.

The default is *64*.

**--transport-id-offset**
+++++++++++++++++++++++++

With SNMP, transport endpoints (network addresses and ports) are identified by
OIDs. Each kind of network transport (e.g. IPv4-over-UDP) has its own OID
prefix, while the instances of it are identified by a longer OID.

When *snmpsim-command-responder* is asked to initialize a transport endpoint,
it will take the prefix OID and append a single sub-OID number starting from
this offset.

The default is one.

**--data-dir**
++++++++++++++

Specifies path to the directory where SNMP simulator should look for simulation
data in form of *.snmprec*, *.snmprec.bz2*, *.snmpwalk* or *.sapwalk* files.
All files found beneath *--data-dir* will be considered as sources of SNMP
simulation data and their paths will be used for SNMP configuration purposes.

Default search path is dependent on the platform. On Linux it is:

* `$HOME/.snmpsim/data`
* `/usr/snmpsim/data`
* `/usr/share/snmpsim/data`
* `<program dir>/data`

**--agent-udpv4-endpoint**
++++++++++++++++++++++++++

Bind SNMP agent to the given UDP-over-IPv4 transport endpoint in the form of
*IP:port*.

Each occurrence of this option creates a new transport endpoint. All SNMP
engines created afterwards (by *--v3-engine-id* option) up to the next
*--agent-* option will reside behind this transport endpoint.

.. code-block:: bash

   $ snmpsim-command-responder --agent-udpv4-endpoint=127.0.0.1:161

.. note::

   Binding ports less than 1024 on UNIX requires superuser privileges.

**--agent-udpv6-endpoint**
++++++++++++++++++++++++++

Bind SNMP agent to the given UDP-over-IPv6 transport endpoint in the form of
*[IP]:port*.

Each occurrence of this option creates a new transport endpoint. All SNMP
engines created afterwards (by *--v3-engine-id* option) up to the next
*--agent-* option will reside behind this transport endpoint.

.. code-block:: bash

   $ snmpsim-command-responder --agent-udpv4-endpoint=[::1]:161

.. note::

   Binding ports less than 1024 on UNIX requires superuser privileges.

Full version command responder options
--------------------------------------

Full version of SNMP command responder is based on SNMPv3 architecture,
it is capable of handling all SNMP versions i.e. 1, 2c qnd 3.

Full version of SNMP command responder understand all options of the lite
version, plus the following SNMPv3-specific options.

**--args-from-file**
++++++++++++++++++++

All command-line options to *snmpsim-command-responder* could be stored in a
file and passes through this option. File could be easier to manage, and does
not impose any limit on the length of the command line.

**--v3-only**
+++++++++++++

SNMP simulator serves simulation data over both SNMP v1/v2c and SNMPv3
protocols. With the *--v3-only* flag in effect, SNMPv1/v2c agents will
not be configured what saves a bit of memory and startup time.

Default is to configure SNMPv1/v2c and SNMPv3.

**--v3-engine-id**
++++++++++++++++++

SNMP engine identifier that creates a new, independent instance of SNMP
engine. All the following *--v3-* options up to another *--v3-engine-id*
option apply to the SNMP engine being configured.

.. code-block:: bash

   snmpsim-command-responder --v3-engine-id=0102030405070809 ...

.. note::

   The *-v3-engine-id* option expects a hex string or `auto` for automaic
   value.

The default is an autogenerated value.

**--v3-context-engine-id**
++++++++++++++++++++++++++

SNMP entity can have access to many instances of the same collection of
MIB objects. Each such collection is called *context*. A context is identified
by the Context Engine ID and a Context Name that identifies the specific
context.

In other words, to identify an individual item of SNMP management information,
four elements are required:

1. a ContextEngineID
2. a ContextName
3. an object type, and
4. its instance identification

The default for *--v3-context-engine-id* option is the same value
as *--v3-engine-id*.

**--v3-user**
+++++++++++++

SNMP USM user name to use for SNMPv3 authentication and authorization purposes.

**--v3-auth-key**
+++++++++++++++++

SNMP USM message authentication key.

.. note::

    Must be 8 or more characters.

**--v3-auth-proto**
+++++++++++++++++++

SNMPv3 message authentication protocol to use. Valid values are:

+--------+----------------+-------------+
| *ID*   |  *Algorithm*   | *Reference* |
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

**--v3-priv-key**
+++++++++++++++++

SNMP USM message encryption key.

.. note::

    Must be 8 or more characters.

**--v3-priv-proto**
+++++++++++++++++++

SNMPv3 message encryption protocol to use. Valid values are:

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
