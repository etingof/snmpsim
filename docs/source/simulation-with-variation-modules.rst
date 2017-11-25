
.. _simulation-with-variation-modules:

Simulation with variation modules
=================================

Without variation modules, simulated SNMP Agents are always static
in terms of data returned to SNMP Managers. They are also read-only.
By configuring particular OIDs or whole subtrees to be routed to
variation modules, that allows you to make returned data changing
over time.

Another way of using variation modules is to gather data from some
external source such as an SQL database or executed process or distant
web-service.

It's also possible to modify simulated values through SNMP SET operation
and store modified values in a database so they will persist over Simulator
restarts.

Variation modules may be used for triggering events at other systems. For
instance the *notification* module will send SNMP TRAP/INFORM SNMP messages
to pre-configured SNMP Managers on SNMP SET request arrival to *snmpsimd.py*.

Finally, variation module API let you develop your own code in Python
to fulfill your special needs and use your variation module with stock
Simulator.

.. _configuring-simulation-with-variation-modules:

Configuring variation modules
-----------------------------

To make use of a variation module you will have to *edit* existing
or create a new data file adding reference to a variation module into 
the *tag* field by means of
:ref:`recording variation modules <recording-with-variation-modules>`.

Remember :ref:`.snmprec file format <snmprec>` is a sequence of lines having
the *OID|TAG|VALUE* fields? With variation module in use, the *TAG* field complies
to its own sub-format - *TAG-ID[:MODULE-ID]*.

Examples
++++++++

The following .snmprec file contents will invoke the *writecache* module and cast
its returned values into ASN.1 OCTET STRING (4) and INTEGER (2) respectively:

.. code-block:: bash

    1.3.6.1.2.1.1.3.0|2:volatilecache|value=42

Whenever a subtree is routed to a variation module, *TAG-ID* part is left out
as there might be no single type for all values within a subtree. Thus the
empty *TAG-ID* sub-field serves as an indicator of a subtree.

For example, the following data file will serve all OIDs under 1.3.6.1.2.1.1
prefix to the "sql" variation module:

.. code-block:: bash

    1.3.6.1.2.1.1|:sql|snmprec

The value part is passed to variation module as-is. It is typically holds some
module-specific configuration or initialization values.

Another example: the following .snmprec line invokes the "notification"
variation module instructing it to send SNMP INFORM message to SNMP
manager at 127.0.01:162 over SNMPv3 with specific SNMP params:

.. code-block:: bash

    1.3.6.1.2.1.1.3.0|67:notification|version=3,user=usr-md5-des,\
        authkey=authkey1,privkey=privkey1,host=127.0.0.1,ntftype=inform,\
        trapoid=1.3.6.1.6.3.1.1.5.2,value=123456

The standard variation modules are installed into the Python site-packages
directory. User can pass Simulator an alternative modules directory through
the command line.

Simulator will load and bootstrap all variation modules it finds. Some
modules can accept initialization parameters (like database connection
credentials) through *snmpsimd.py* *--variation-module-options* command-line
parameter.

For example, the following Simulator invocation will configure its
*sql* variation module to use sqlite database (sqlite3 Python module)
and /var/tmp/snmpsim.db database file:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:sqlite3,\
        database:/var/tmp/snmpsim.db

IF you are using multiple database connections or database types
all through the *sql* variation module, you could refer to each
module instance in *.snmprec* files through a so-called variation
module alias.

The following command-line runs Simulator with two instances of the
*involatilecache* variation module (dbA & dbB) each instance using
distinct database file for storing their persistent values:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=writecache=dbA:file:/var/tmp/fileA.db \
        --variation-module-options=writecache=dbB:file:/var/tmp/fileB.db

The syntax for *--variation-module-options=* module configuration string is
comma-separated list of semicolon-separated name:value pairs:

.. code-block:: bash

    --variation-module-options=<module[=alias]:<[nameA:valueA,nameB:valueB,...]>>

With exception for the first semicolon (which is considered to be a part
of module reference), the rest of separators could potentially intervene
with values. In that case user could use a doubled or tripled separator
tokens as an escaping aid:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=writecache:file::C:\TEMP\fileA.db

The same separator escaping method works for module options in *.snmprec* value
field. The only difference is that *.snmprec* value syntax uses equal sign and
commands as separators.

.. _standard-variation-modules:

Standard variation modules
--------------------------

The following variation modules are shipped with SNMP Simulator:

* The :ref:`numeric <variate-numeric>` module produces a non-decreasing
  sequence of integers over time
* The :ref:`notification <variate-notification>` module sends SNMP TRAP/INFORM
  messages to distant SNMP entity
* The :ref:`writecache <variate-writecache>` module accepts and stores (in memory/file)
  SNMP variable-bindings being modified through SNMP SET command
* The :ref:`sql <variate-sql>` module reads/writes var-binds from/to a SQL database
* The :ref:`redis <variate-redis>` module reads/writes var-binds from/to a no-SQL
  key-value store
* The :ref:`delay <variate-delay>` module delays SNMP response by specified
  or random time
* The :ref:`error <variate-error>` module flag errors in SNMP response PDU
* The :ref:`multiplex <variate-multiplex>` module uses a time series of .snmprec
  files picking one at a time.
* The :ref:`subprocess <variate-subprocess>` module executes external process and
  puts its stdout values into response

.. _variate-numeric:

Numeric module
++++++++++++++

The numeric module maintains and returns a changing in time integer value.
The law and rate of changing is configurable. This module is per-OID
stateful and configurable.

The numeric module accepts the following comma-separated key=value parameters
in *.snmprec* value field:

* min - the minimum value ever stored and returned by this module.
  Default is 0.
* max - the maximum value ever stored and returned by this module.
  Default is 2\*\*32 or 2\*\*64 (Counter64 type).
* initial - initial value. Default is min.
* atime - if non-zero, uses current time for value generation, not Simulator uptime.
* wrap - if zero, generated value will freeze when reaching 'max'. Otherwise
  generated value is reset to 'min'.
* function - defines elapsed-time-to-generated-value relationship. Can be
  any of reasonably suitable mathematical function from the
  math module such as sin, log, pow etc. The only requirement
  is that used function accepts a single integer argument.
  Default is x = f(x).
* rate - elapsed time scaling factor. Default is 1.
* scale - function value scaling factor. Default is 1.
* offset - constant value by which the return value increases on each
  invocation. Default is 0.
* deviation - random deviation maximum. Default is 0 which means no
  deviation.
* cumulative - if non-zero sums up previous value with the newly
  generated one. This is important when simulating COUNTER values.

This module generates values by execution of the following formula:

.. code-block:: python

  TIME = TIMENOW if atime else UPTIME

  v = function(TIME * rate) * scale + offset + RAND(-deviation, deviation)

  v = v + prev_v if cumulative else v

Examples
~~~~~~~~

.. code-block:: bash

    # COUNTER object
    1.3.6.1.2.1.2.2.1.13.1|65:numeric|scale=10,deviation=1,function=cos,cumulative=1,wrap=1

    # GAUGE object
    1.3.6.1.2.1.2.2.1.14.1|66:numeric|min=5,max=50,initial=25

You are welcome to try the *numeric* module in action at our online
:ref:`public SNMP simulation service <snmp-simulation-service>`:

.. code-block:: bash

    $ snmpget -v2c -c variation/virtualtable demo.snmplabs.com  \
        IF-MIB::ifLastChange.1 IF-MIB::ifInOctets.1
    IF-MIB::ifLastChange.1 = Timeticks: (16808012) 1 day, 22:41:20.12
    IF-MIB::ifInOctets.1 = Counter32: 30374688

The numeric module can be used for simulating INTEGER, Counter32, Counter64,
Gauge32, TimeTicks objects.

.. _variate-delay:

Delay module
++++++++++++

The delay module postpones SNMP request processing for specified number of
milliseconds.

Delay module accepts the following comma-separated *key=value* parameters
in *.snmprec* value field:

* *value* - holds the var-bind value to be included into SNMP response.
  In case of a string value containing commas, use the *hexvalue*
  key instead.
* *hexvalue* - holds the var-bind value as a sequence of ASCII codes in hex
  form. Before putting it into var-bind, hexvalue contents will
  be converted into ASCII text.
* *wait* - specifies for how many milliseconds to delay SNMP response.
  Default is 500ms. If the value exceeds 999999, request will never
  be answered (PDU will be dropped right away).
* *deviation* - random delay deviation ranges (ms). Default is 0 which means
  no deviation.
* *vlist* - a list of triples *comparison:constant:delay* to use on SET
  operation for choosing delay based on value supplied in request.
  The following comparison operators are supported: *eq*, *lt*, *gt*.
* *tlist* - a list of triples *comparison:time:delay* to use for choosing
  request delay based on time of day (seconds, UNIX time).
  The following comprison operators are supported: *eq*, *lt*, *gt*.

Examples
~~~~~~~~

The following entry makes Simulator responding with an integer value of
6 delayed by 0.1sec +- 0.2 sec (negative delays are casted into zeros):

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.3.1|2:delay|value=6,wait=100,deviation=200

Here the hexvalue takes shape of an OCTET STRING value '0:12:79:62:f9:40'
delayed by exactly 0.8 sec:

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.6.1|4:delay|hexvalue=00127962f940,wait=800

This entry drops PDU right away so the Manager will timed out:

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.7.1|2:delay|wait=1000000

The following entry uses module default on GET/GETNEXT/GETBULK operations.
However delays response by 0.1 sec if request value is exactly 0 and delays
response by 1 sec on value equal to 1.

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.8.1|2:delay|vlist=eq:0:100:eq:1:1000,value=1

The entry that follows uses module default on GET/GETNEXT/GETBULK operations,
however delays response by 0.001 sec if request value is exactly 100,
uses module default on values >= 100 but <= 300 (0.5 sec), and drops request
on values > 300:

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.9.1|67:delay|vlist=lt:100:1:gt:300:1000000,value=150

The next example will simulate an unavailable Agent past 01.04.2013 (1364860800
in UNIX time):

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.10.1|67:delay|tlist=gt:1364860800:1000000,value=150

.. note::

    Since SNMP Simulator is internally an asynchronous, single-thread
    application, any delayed response will block all concurrent requests
    processing as well.

.. _variate-error:

Error module
++++++++++++

The error module flags a configured error at SNMP response PDU.

Error module accepts the following comma-separated key=value parameters
in *.snmprec* value field:


* *op* - either of *get*, *set* or *any* values to indicate SNMP operation
  that would trigger error response. Here *get* also enables GETNEXT
  and GETBULK operations. Default is *any*.
* *value* - holds the var-bind value to be included into SNMP response.
  In case of a string value containing commas, use the *hexvalue* key
  instead.
* *hexvalue* - holds the var-bind value as a sequence of ASCII codes in hex
  form. Before putting it into var-bind, hexvalue contents will
  be converted into ASCII text.
* *status* - specifies error to be flagged. The following SNMP errors codes are
  supported:

  - *genError*
  - *noAccess*
  - *wrongType*
  - *wrongValue*
  - *noCreation*
  - *inconsistentValue*
  - *resourceUnavailable*
  - *commitFailed*
  - *undoFailed*
  - *authorizationError*
  - *notWritable*
  - *inconsistentName*
  - *noSuchObject*
  - *noSuchInstance*
  - *endOfMib*

* *vlist* - a list of triples (comparison:constant:error) to use as an access
  list for SET values.

  The following comparison operators  are supported:

  - *eq*
  - *lt*
  - *gt*

  The following SNMP errors are supported (case-insensitive):

  - *genError*
  - *noAccess*
  - *wrongType*
  - *wrongValue*
  - *noCreation*
  - *inconsistentValue*
  - *resourceUnavailable*
  - *commitFailed*
  - *undoFailed*
  - *authorizationError*
  - *notWritable*
  - *inconsistentName*
  - *noSuchObject*
  - *noSuchInstance*
  - *endOfMib*

Examples
~~~~~~~~

.. code-block:: bash

    1.3.6.1.2.1.2.2.1.1.1|2:error|op=get,status=authorizationError,value=1
    1.3.6.1.2.1.2.2.1.2.1|4:error|op=set,status=commitfailed,hexvalue=00127962f940
    1.3.6.1.2.1.2.2.1.3.1|2:error|vlist=gt:2:wrongvalue,value=1
    1.3.6.1.2.1.2.2.1.6.1|4:error|status=noaccess

The first entry flags *authorizationError* on GET* and no error
on SET. Second entry flags *commitfailed* on SET but responds without errors
to GET*. Third entry fails with *wrongvalue* only on SET with values > 2.
Finally, forth entry always flags *noaccess* error.

.. _variate-writecache:

Writecache module
+++++++++++++++++

The *writecache* module lets you make particular OID at a *.snmprec* file
writable via SNMP SET operation. The new value will be stored in Simulator
process's memory or disk-based data store and communicated back on SNMP
GET/GETNEXT/GETBULK operations. Data saved in disk-based data store will
NOT be lost upon Simulator restart.

Module initialization allows for passing a name of a database file to be
used as a disk-based data store:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=writecache:file:/tmp/shelves.db

All modifed values will be kept and then subsequently used on a per-OID
basis in the specified file. If data store file is not specified, the
*writecache* module will keep all its data in [volatile] memory.

The *writecache* module accepts the following comma-separated *key=value*
parameters in *.snmprec* value field:

* *value* - holds the var-bind value to be included into SNMP response.
  In case of a string value containing commas, use *hexvalue*
  instead.
* *hexvalue* - holds the var-bind value as a sequence of ASCII codes in hex
  form. Before putting it into var-bind, hexvalue contents will be converted
  into ASCII text.
* *vlist* - a list of triples *comparison:constant:error* to use as an access
  list for SET values.

  The following comparison operators  are supported:

  - *eq*
  - *lt*
  - *gt*

  The following SNMP errors are supported (case-insensitive):

  - *genError*
  - *noAccess*
  - *wrongType*
  - *wrongValue*
  - *noCreation*
  - *inconsistentValue*
  - *resourceUnavailable*
  - *commitFailed*
  - *undoFailed*
  - *authorizationError*
  - *notWritable*
  - *inconsistentName*
  - *noSuchObject*
  - *noSuchInstance*
  - *endOfMib*

Examples
~~~~~~~~

.. code-block:: bash

    1.3.6.1.2.1.1.3.0|2:writecache|value=42

In the above configuration, the initial value is 42 and can be modified by
the *snmpset* command (assuming correct community name and Simulator is
running locally).

.. code-block:: bash

    $ snmpset -v2c -c community localhost 1.3.6.1.2.1.1.3.0 i 24

A more complex example involves using an access list. The following example
allows only values of 1 and 2 to be SET:

.. code-block:: bash

    1.3.6.1.2.1.1.3.0|2:writecache|value=42,vlist=lt:1:wrongvalue:gt:2:wrongvalue

Any other SET values will result in SNNP WrongValue error in response.

.. note::

    An attempt to SET a value of incompatible type will also result
    in error.

.. _variate-multiplex:

Multiplex module
++++++++++++++++

The multiplex module allows you to serve many snapshots for a single Agent
picking just one snapshot at a time for answering SNMP request. That
simulates a more natural Agent behaviour including the set of OIDs changing
in time.

This module is usually configured to serve an OID subtree in an *.snmprec*
file entry.

The multiplex module accepts the following comma-separated *key=value*
parameters in *.snmprec* value field:

* *dir* - path to *.snmprec* files directory. If path is not absolute, it
  is interpreted relative to Simulator's *--data-dir*. The
  *.snmprec* files names here must have numerical names ordered
  by time.
* *period* - specifies for how long to use each *.snmprec* snapshot before
  switching to the next one. Default is 60 seconds.
* *wrap* - if true, instructs the module to cycle through all available
  *.snmprec* files. If false, the system stops switching *.snmprec*
  files as it reaches the last one. Default is false.
* *control* - defines a new OID to be used for switching *.snmprec* file
  via SNMP SET command.

Examples
~~~~~~~~

.. code-block:: bash

    1.3.6.1.2.1.2|:multiplex|dir=variation/snapshots,period=10.0
    1.3.6.1.3.1.1|4|snmprec

The variation/snapshots/ directory contents is a name-ordered collection
of *.snmprec* files:

.. code-block:: bash

    $ ls -l /usr/local/share/snmpsim/data/variation/snapshots
    -rw-r--r--  1 root  staff  3145 Mar 30 22:52 00000.snmprec
    -rw-r--r--  1 root  staff  3145 Mar 30 22:52 00001.snmprec
    -rw-r--r--  1 root  staff  3145 Mar 30 22:52 00002.snmprec
    ...

Simulator can use each of these files only once through its
configured time series. To make it cycling over them, use *wrap*
option.

The *.snmprec* files served by the multiplex module can not include references
to variation modules.

In cases when automatic, time-based *.snmprec* multiplexing is not
applicable for simulation purposes, *.snmprec* selection can be configured:
</p>

.. code-block:: bash

    1.3.6.1.2.1.2|:multiplex|dir=variation/snapshots,control=1.3.6.1.2.1.2.999

The following command will switch multiplex module to use the first
*.snmprec* file for simulation:

.. code-block:: bash

    $ snmpset -v2c -c variation/multiplex localhost 1.3.6.1.2.1.2.999 i 0

Whenever *control* OID is present in multiplex module options, the
time-based multiplexing will not be used.

.. _variate-subprocess:

Subprocess module
+++++++++++++++++

The *subprocess* module can be used to execute an external program
passing it request data and using its stdout output as a response value.

Module invocation supports passing a *shell* option which (if true) makes
Simulator using shell for subprocess invocation. Default is True on
Windows platform and False on all others.

.. warning::

  With *shell=True*, UNIX shell gets into the pipeline what compromises
  security.

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=subprocess:shell:1

Value part of *.snmprec* line should contain space-separated path
to external program executable followed by optional command-line
parameters.

SNMP request parameters could be passed to the program to be executed
by means of macro variables. With subprocess module, macro variables
names always carry '@' sign at front and back (e.g. @MACRO@).

Macros
~~~~~~

* *@DATAFILE@* - resolves into the *.snmprec* file selected by
  SNMP Simulator for serving current request
* *@OID@* - resolves into an OID of *.snmprec* line selected for serving
  current request
* *@TAG@* - resolves into the <tag> component of *.snmprec* line selected
  for serving current request
* *@ORIGOID@* - resolves into currently processed var-bind OID
* *@ORIGTAG@* - resolves into value type of currently processed var-bind
* *@ORIGVALUE@* - resolves into value of currently processed var-bind
* *@SETFLAG@* - resolves into '1' on SNMP SET, '0' otherwise
* *@NEXTFLAG@* - resolves into '1' on SNMP GETNEXT/GETBULK, '0' otherwise
* *@SUBTREEFLAG@* - resolves into '1' if the *.snmprec* file line selected
  for processing current request serves a subtree of OIDs rather than a
  single specific OID
* *@TRANSPORTDOMAIN@* - SNMP transport domain as an OID. It has a one-to-one
  relationship with local interfaces Simulator is configured to listen at
* *@TRANSPORTADDRESS@* - peer transport address
* *@SECURITYMODEL@* - SNMPv3 Security Model
* *@SECURITYNAME@* - SNMPv3 Security Name
* *@SECURITYLEVEL@* - SNMPv3 Security Level
* *@CONTEXTNAME@* - SNMPv3 Context Name

Examples
~~~~~~~~

.. code-block:: bash

    1.3.6.1.2.1.1.1.0|4:subprocess|echo SNMP Context is @DATAFILE@, received \
      request for @ORIGOID@, matched @OID@, received tag/value \
      "@ORIGTAG@"/"@ORIGVALUE@", would return value tagged @TAG@, SET request \
      flag is @SETFLAG@, next flag is @NEXTFLAG@, subtree flag is \
      @SUBTREEFLAG@
    1.3.6.1.2.1.1.3.0|2:subprocess|date +%s

The first entry simply packs all current macro variables contents as a
response string my printing them to stdout with echo, second entry invokes
the UNIX date command instructing it to report elapsed UNIX epoch time.

Note *.snmprec* tag values -- executed program's stdout will be casted into
appropriate type depending of tag indication.

.. _variate-notification:

Notification module
+++++++++++++++++++

The *notification* module can send SNMP TRAP/INFORM notifications to
distant SNMP engines by way of serving SNMP request sent to Simulator.
In other words, SNMP message sent to Simulator can trigger sending
TRAP/INFORM message to pre-configured targets.

.. note::

    No new process is created when sending SNMP notification -- *snmpsimd*'s
    own SNMP engine is reused.

The *notification* module accepts the following comma-separated *key=value*
parameters in *.snmprec* value field:

* *value* - holds the variable-bindings value to be included into SNMP
  response message.
* *op* - either of *get*, *set* or *any* values to indicate SNMP operation that
  would trigger notification. Here *get* also enables GETNEXT and GETBULK
  operations. Default is *set*.
* *vlist* - a list of pairs *comparison:constant* to use as event
  triggering criteria to be compared against SET values.
  The following comparisons are supported: *eq*, *lt*, *gt*.
* *version* - SNMP version to use (1,2c,3).
* *ntftype* - indicates notification type. Either *trap* or *inform*.
* *community* - SNMP community name. For v1, v2c only. Default is *public*.
* *trapoid* - SNMP TRAP PDU element. Default is *coldStar*.
* *uptime* - SNMP TRAP PDU element. Default is local SNMP engine uptime.
* *agentaddress* - SNMP TRAP PDU element. For v1 only. Default is local SNMP
  engine address.
* *enterprise* - SNMP TRAP PDU element. For v1 only.
* *user* - USM username. For v3 only.
* *authproto* - USM auth protocol. For v3 only. Either *md5* or *sha*.
  Default is *md5*.
* *authkey* - USM auth key. For v3 only.
* *privproto* - USM encryption protocol. For v3 only. Either *des* or *aes*.
  Default is *des*.
* *privkey* - USM encryption key. For v3 only.
* *proto* - transport protocol. Either *udp* or *udp6*. Default is *udp*.
* *host*- hostname or network address to send notification to.
* *port* - UDP port to send notification to. Default is 162.
* *varbinds* - a semicolon-separated list of *OID:TAG:VALUE:OID:TAG:VALUE...*
  of var-binds to add into SNMP TRAP PDU.

  The following *TAG* values are recognized:

  - *s* - OctetString (expects character string)
  - *h* - OctetString (expects hex string)
  - *i* - Integer32
  - *o* - ObjectName
  - *a* - IpAddress
  - *u* - Unsigned32
  - *g* - Gauge32
  - *t* - TimeTicks
  - *b* - Bits
  - *I* - Counter64

Examples
~~~~~~~~

The following three *.snmprec* lines will send SNMP v1, v2c
and v3 notifications whenever Simulator is processing GET* and/or SET
request for configured OIDs:

.. code-block:: bash

    1.3.6.1.2.1.1.1.0|4:notification|op=get,version=1,community=public,\
      proto=udp,host=127.0.0.1,port=162,ntftype=trap,\
      trapoid=1.3.6.1.4.1.20408.4.1.1.2.0.432,uptime=12345,agentaddress=127.0.0.1,\
      enterprise=1.3.6.1.4.1.20408.4.1.1.2,\
      varbinds=1.3.6.1.2.1.1.1.0:s:snmpsim agent:1.3.6.1.2.1.1.3.0:i:42,\
      value=SNMPv1 trap sender

    1.3.6.1.2.1.1.2.0|6:notification|op=set,version=2c,community=public,\
      host=127.0.0.1,ntftype=trap,trapoid=1.3.6.1.6.3.1.1.5.1,\
      varbinds=1.3.6.1.2.1.1.1.0:s:snmpsim agent:1.3.6.1.2.1.1.3.0:i:42,\
      value=1.3.6.1.1.1

    1.3.6.1.2.1.1.3.0|67:notification|version=3,user=usr-md5-des,authkey=authkey1,\
      privkey=privkey1,host=127.0.0.1,ntftype=inform,trapoid=1.3.6.1.6.3.1.1.5.2,\
      value=123456

.. note::

    The delivery status of INFORM notifications is not communicated
    back to the SNMP Manager working with Simulator.

.. _variate-sql:

SQL module
++++++++++

The *sql* module lets you keep subtrees of OIDs and their values in a
relational database. All SNMP operations are supported including
transactional SET.

Module invocation requires passing database type (sqlite3, psycopg2,
MySQL and any other compliant to 
`Python DB-API <http://www.python.org/dev/peps/pep-0249/#id7">`_
and importable as a Python module) and connect string which is database
dependant.

Besides DB-specific connect string key-value parameters,
sql module supports the following comma-separated key:value
options whilst running in recording mode:

* *dbtype* - SQL DBMS type in form of Python DPI API-compliant module.
  It will be imported into Python as specified.
* *dbtable* - Default SQL table name to use for storing recorded
  snapshot. It is used if table name is not specified in *.snmprec* file.
* *isolationlevel* - SQL transaction
  `isolation level <https://en.wikipedia.org/wiki/Isolation_(database_systems)>`_.
  Allowed values are:

  - *0* - READ UNCOMMITTED
  - *1* - READ COMMITTED
  - *2* - REPEATABLE READ
  - *3* - SERIALIZABLE

  Default is READ COMMITTED.

Database connection
~~~~~~~~~~~~~~~~~~~

For SQLite database invocation use the following command:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:sqlite3,database:/var/tmp/sqlite.db

To use a MySQL database for OID/value storage, the following Simulator
invocation would work:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:mysql.connector,\
      host:127.0.0.1,port:3306,user:snmpsim,password:snmpsim,database:snmpsim

assuming you have the
`MySQL Connector/Python driver <href="http://dev.mysql.com/doc/refman/5.5/en/connector-python.html>`_
is installed on the SNMP Simulator machine and a MySQL server running at 127.0.0.1 with MySQL user/password
snmpsim/snmpsim having full access to a database *snmpsim*

Another variation of MySQL server installation setup on a UNIX system employs
UNIX domain socket for client-server communication. In that case the following
command-line for *.snmprec* might work:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:mysql.connector,
      unix_socket:/var/run/mysql/mysql.sock,user:snmpsim,password:snmpsim,
      database:snmpsim

Alternatively, the `MySQL for Python <https://sourceforge.net/projects/mysql-python/>`_ package
can be used for Simulator to MySQL connection:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:MySQLdb,host:127.0.0.1,
      port:3306,user:snmpsim,passwd:snmpsim,db:snmpsim

If you wish to use `PostgresSQL <http://www.postgresql.org/>`_
database for OID/value storage, the following command line will do the job:

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=sql:dbtype:psycopg2,
      user:snmpsim,password:snmpsim,database:snmpsim

assuming you have the
`Psycopg Python adapter <http://initd.org/psycopg/>`_ is
installed on the SNMP Simulator machine and a PostgreSQL server running locally
(accessed through default UNIX domain socket) with PostgreSQL user/password
snmpsim/snmpsim having full access to a database *snmpsim*.

Simulation data configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *.snmprec* value is expected to hold database table name to keep
all OID-value pairs served within selected *.snmprec* line. This table
can either be created automatically whenever *sql* module is invoked in
:ref:`recording mode <record-sql>` or can be created and populated by
hand. In the latter case table layout should be as follows:

.. code-block:: bash

  CREATE TABLE <tablename> (oid text,
                            tag text,
                            value text,
                            maxaccess text)

The most usual setup is to keep many OID-value pairs in a database
table referred to by a *.snmprec* line serving a subtree of OIDs:

.. code-block:: bash

    1.3.6.1.2.1.1|:sql|snmprec

In the above case all OIDs under 1.3.6.1.2.1.1 prefix will be
handled by a sql module using 'snmprec' table.

.. note::

    To make SQL's ORDER BY clause working with OIDs, each sub-OID stored
    in the database (in case of manual database population) must be
    left-padded with a good bunch of spaces (each sub-OID width is
    10 characters).

.. _variate-redis:

Redis module
++++++++++++

The *redis* module lets you keep subtrees of OIDs and their values in a no-SQL
key-value store. Besides complete SNMP operations support, Redis server-side
Lua scripts are also supported at both variation and :ref:`recording <record-redis>`
stages.

For redis variation module to work you must also have the
`redis-py <https://github.com/andymccurdy/redis-py/tree/master/redis>`_
Python module installed on your system. Module invocation requires passing
Redis database connection string. The following parameters are supported:

* *host* - Redis hostname or IP address.
* *port* - Redis TCP port the server is listening on.
* *unix_socket* - UNIX domain socket Redis server is listening on.
* *db* - Redis database number.
* *password* - Redis database admission password.

.. code-block:: bash

    $ snmpsimd.py --variation-module-options=redis:host:127.0.0.1,port:6379,db:0


SNMP variable-bindings recorded by Simulator in a single recording session is
placed into a dedicated key namespace called "key space". This allows for keeping
many versions of the same oid-value pair either belonging to different Agents or
recorded at different times. These key spaces are organized by pre-pending
a session-unique "key space" to each key put into Redis.

Simulator keeps recorded SNMP var-binds in three types of Redis data structures:

* Redis `String <http://redis.io/commands#string>`_ where each key is
  composed from key space and an OID joint with a dash
  *<key-space>-<oid>*. Values are SNMP data type tag and value in
  :ref:`snmprec format <snmprec>`. This is where simulation
  data is stored.
* Redis `LIST <http://redis.io/commands#list>`_ object keyed
  *<key-space>|oids_ordering* where each element is a key from the
  String above. The purpose of this structure is to order
  OIDs what is important for serving SNMP GETNEXT/GETBULK queries.
* Redis `LIST <http://redis.io/commands#list>`_ object keyed
  *<key-spaces-id>* where each element is a <key-space> from the
  LIST above. The purpose of this structure is to consolidate many key
  spaces into a sequence to form simulation data time series and ease
  switching key spaces during simulation.

The data structure above can be created manually or automatically
whenever redis module is invoked in :ref:`recording mode <record-redis>`.

.. note::

    To make string-typed OIDs comparable, sub-OIDs
    of original OIDs must be left-padded with a good bunch of spaces 
    (up to 9) so that 1.3.6 will become '         1.         3.         6'.

The .snmprec value is expected to hold more Redis database access
parameters, specific to OID-value pairs served within selected
*.snmprec* line.

* *key-spaces-id* - Redis key used to store a sequence of key-spaces referring
  to oid-value collections used for simulation.
* *period* - number of seconds to switch from one key-space to another within
  the key-spaces-id list.
* *evalsha* - Redis server side 
  `Lua script <http://redis.io/commands#scripting>`_ to use for
  accessing oid-value pairs stored in Redis. If this option is not given, 
  bare Redis GET/SET commands will be used instead.

Examples
~~~~~~~~

The most usual setup is to keep many OID-value pairs in a Redis database
referred to by a *.snmprec* line serving a subtree of OIDs:

.. code-block:: bash

    1.3.6.1.2.1.1|:redis|key-spaces-id=1234

In the above case all OIDs under 1.3.6.1.2.1.1 prefix will be
handled by redis module using key spaces stored in "1234" Redis list.

For example, the "1234" keyed list can hold the following key spaces:
["4321", "4322", "4323"]. Then the following keys can be stored for
1.3.6.1.2.1.1.3.0 OID:

.. code-block:: bash

    "4321-<9 spaces>.1<9 spaces>.3<9 spaces>.6 ... <9 spaces>.3<9 spaces>.0" = "67|812981"
    "4322-<9 spaces>.1<9 spaces>.3<9 spaces>.6 ... <9 spaces>.3<9 spaces>.0" = "67|813181"
    "4323-<9 spaces>.1<9 spaces>.3<9 spaces>.6 ... <9 spaces>.3<9 spaces>.0" = "67|814233"

If *period* parameter is passed through the *.snmprec* record, Simulator will
automatically change key space every *period* seconds when gathering data
for SNMP responses. 

The *key-spaces-id* Redis list can also be manipulated by an external
application at any moment for the purpose of switching key spaces while
Simulator is running. Simulated values can also be modified on-the-fly
by an external application. However, when adding/removing OIDs, not just
modifying simulation data, care must be taken to keep the 
<key space>-oids_ordering list ordered and synchronized with the
collection of <key space>-OID keys being used for storing simulation
data.

Besides using an external application for modifying simulation data, custom
`Lua script <http://redis.io/commands#scripting>`_ can be used
for dynamic response and/or stored data modification. For example, the
following *.snmprec* entry will invoke server-side Lua script stored under
the name of "d94bf1756cda4f55bac9fe9bb872f" when getting/setting
Redis keys:

.. code-block:: bash

    1.3.6.1.2.1.1|:redis|key-spaces-id=1234,evalsha=d94bf1756cda4f55bac9fe9bb872f

Here's an example Lua script, carrying no additional logic, stored at Redis
server using the `SCRIPT LOAD <http://redis.io/commands/script-load>`_
Redis command:

.. code-block:: bash

    $ redis-cli
    127.0.0.1:6379> script load  "
      if table.getn(ARGV) > 0 then
        return redis.call('set', KEYS[1], ARGV[1])
      else
        return redis.call('get', KEYS[1])
      end
    "
    "d94bf1756cda4f55bac9fe9bb872f"
    127.0.0.1:6379>

SNMP Simulator will perform SET/GET operations through its *evalsha* script
like this:

.. code-block:: bash

    $ redis-cli
    127.0.0.1:6379> evalsha "d94bf1756cda4f55bac9fe9bb872f" 1 "4321|1.
             3.         6.         1.         2.         1.        2.      1.
             1.         0" "4|linksys router"
    127.0.0.1:6379> evalsha "d94bf1756cda4f55bac9fe9bb872f" 1 "4321|1.
             3.         6.         1.         2.         1.        2.      1.
             1.         0"
    "4|linksys router"
    127.0.0.1:6379>

A much more complex Lua scripts could be written to dynamically modify other
parts of the database, sending messages to other Redis-backed applications
through Redis's `Publish/Subscribe <http://redis.io/commands#pubsub>`_
facility.

Writing variation modules
-------------------------

Whenever you consider coding your own variation module, take a look at the
existing ones. The API is very simple - it basically takes three Python 
functions (init, process, shutdown) where process() is expected to return
a var-bind pair per each invocation.
