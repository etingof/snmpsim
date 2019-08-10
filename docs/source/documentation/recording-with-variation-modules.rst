
.. _recording-with-variation-modules:

Recording with variation modules
================================

Some valuable simulation information may also be collected in the process
of recording snapshots off the live SNMP Agent. Examples include changes in
the set of OIDs in time, changes in numeric values, request processing times
and so on. To facilitate capturing such information, some of the stock
variation modules support snapshots recording mode.

To invoke a variation module while recording SNMP Agent with
the :ref:`snmprec.py <snmprec.py>` tool, pass its name via the *--variation-module*
command-line option. Additional variation module parameters could also be passed
through the *--variation-module-options* switch.

The following standard modules support the recording feature:

* The :ref:`numeric <record-numeric>` module produces a non-decreasing
  sequence of integers over time
* The :ref:`sql <record-sql>` module reads/writes var-binds from/to a SQL database
* The :ref:`redis <record-redis>` module reads/writes var-binds from/to a no-SQL
  key-value store
* The :ref:`delay <record-delay>` module delays SNMP response by specified
  or random time
* The :ref:`multiplex <record-multiplex>` module uses a time series of *.snmprec*
  files picking one at a time.

.. _record-numeric:

Numeric module
--------------

The numeric module can be used for capturing initial values of
Managed Objects and calculating a coefficient to a linear function
in attempt to approximate live values changes in time. In case value
change law is not linear, custom approximation function should be used
instead.

The numeric module supports the following comma-separated key:value
options whilst running in recording mode:

* *taglist* - a dash-separated list of *.snmprec* tags indicating SNMP
  value types to apply numeric module to.

  Valid tags are:

  - 2 - Integer
  - 65 - Counter32
  - 66 - Gauge32
  - 67 - TimeTicks
  - 70 - Counter64

  Default is empty list.

* *iterations* - number of recording cycles to run over the same
  portion of SNMP agent MIB. There's no point in values
  beyond 2 for purposes of modelling approximation function.
  Default is 1.
* *period* - Agent walk period in seconds. Default is 10 seconds.
* *addon* - a single *.snmprec* record scope *key=value* parameter for the
  *numeric* module to be used whilst running in variation mode.
  Multiple add-on parameters can be used. Default is empty.

Examples
++++++++

In the examples the :ref:`snmprec.py <snmprec.py>` tool will be used.

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 \
      --variation-module=numeric \
      --variation-module-options=taglist:65,iterations:2,period:15 \
    Scanning "/usr/local/share/snmpsim/variation" directory for variation
    modules...numeric module loaded
    SNMP version 2c
    Community name: public
    Querying UDP/IPv4 agent at demo.snmplabs.com:161
    Initializing variation module:
        numeric...OK
    numeric: waiting 0.77 sec(s), 111 OIDs dumped, 1 iterations remaining...
    ...
    1.3.6.1.2.1.2.2.1.6.4|4x|008d120f4fa4
    1.3.6.1.2.1.2.2.1.7.1|2|1
    1.3.6.1.2.1.2.2.1.9.2|67|0
    1.3.6.1.2.1.2.2.1.10.1|65:numeric|rate=3374,initial=641734,increasing=1
    1.3.6.1.2.1.2.2.1.10.2|65:numeric|rate=0,initial=0,increasing=1
    1.3.6.1.2.1.2.2.1.10.4|65:numeric|rate=1159,initial=32954879,increasing=1
    1.3.6.1.2.1.2.2.1.11.1|65:numeric|rate=86,initial=12238,increasing=1
    1.3.6.1.2.1.2.2.1.21.1|66|0
    ...
    Shutting down variation modules:
        numeric...OK
    OIDs dumped: 224, elapsed: 15.53 sec, rate: 20.00 OIDs/sec

In the above example we have run two iterations against a subset of
Managed Objects at an Agent requesting numeric module to configure
itself into generated *.snmprec* data for Counter32-typed objects (ID 65).

Produced *.snmprec* file could be used for simulation as-is or edited
by hand to change variation module behaviour on on a per-OID basis.

.. _record-delay:

Delay module
------------

The delay module can be used for capturing request processing time
when recording SNMP agent.

Examples
++++++++

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 \
      --variation-module=delay
    Scanning "/usr/local/share/snmpsim/variation" directory for variation
    modules...delay module loaded
    SNMP version 2c
    Community name: public
    Querying UDP/IPv4 agent at demo.snmplabs.com:161
    Initializing variation module:
        delay...OK
    1.3.6.1.2.1.2.1.0|2:delay|value=5,wait=8
    1.3.6.1.2.1.2.2.1.1.1|2:delay|value=1,wait=32
    1.3.6.1.2.1.2.2.1.6.4|4x:delay|hexvalue=008d120f4fa4,wait=20
    ...
    Shutting down variation modules:
        delay...OK
    OIDs dumped: 224, elapsed: 15.53 sec, rate: 20.00 OIDs/sec

Produced *.snmprec* file could be used for Simulation as-is or edited
by hand to change delay variation.

.. _record-multiplex:

Multiplex module
----------------

The multiplex module can record a series of snapshots at specified period
of time. Recorded *.snmprec* snapshots could then be used for simulation
by multiplex module.

The multiplex module supports the following comma-separated *key:value*
options whilst running in recording mode:

* *dir* - directory for produced *.snmprec* files
* *iterations* - number of recording cycles to run over the same
  portion of SNMP agent MIB. There's no point in values
  beyond 2 for purposes of modelling approximation function.
  Default is 1.
* *period* - Agent walk period in seconds. Default is 10 seconds.
* *addon* - a single *.snmprec* record scope *key=value* parameter for the
  *multiplex* module to be used whilst running in variation mode.
  Multiple add-on parameters can be used. Default is empty.

Examples
++++++++

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 \
      --output-file=data/multiplex.snmprec \
      --variation-module=multiplex \
      --variation-module-options=dir:data/multiplex,iterations:5,period:15
    Scanning "/usr/local/share/snmpsim/variation" directory for variation modules...multiplex module loaded
    SNMP version 2c
    Community name: public
    Querying UDP/IPv4 agent at demo.snmplabs.com:161
    Initializing variation module:
        multiplex...OK
    multiplex: writing into data/multiplex/00000.snmprec file...
    multiplex: waiting 14.78 sec(s), 45 OIDs dumped, 5 iterations remaining...
    ...
    multiplex: writing into data/multiplex/00005.snmprec file...
    Shutting down variation modules:
        multiplex...OK
    OIDs dumped: 276, elapsed: 75.76 sec, rate: 3.64 OIDs/sec

Besides individual *.snmprec* snapshots, the "main" *.snmprec* file
will also be written:

.. code-block:: bash

    $ cat data/multiplex.snmprec
    1.3.6.1.2.1.2|:multiplex|period=15.00,dir=data/multiplex

where the multiplex module is configured for specific OID subtree (actually,
specified in *--start-oid*).

Although multiplex-generated *.snmprec* files can also be addressed directly
by Simulator, to benefit from the time series nature of the collected data,
it's better to simulate based on the "main" *.snmprec* file and the multiplex
variation module.

.. _record-sql:

SQL module
----------

The *sql* module can record a snapshot of SNMP agent's set of Managed Objects
and store it in a SQL database. Recorded snapshots could then be used
for simulation by the *sql* module running in variation mode.

Module configuration parameters described on the :ref:`simulation <variate-sql>`
page are also applicable to the recording.

Examples
++++++++

Running with SQLite DB backend:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com
      --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3
      --output-file=data/sql.snmprec
      --variation-module=sql
      --variation-module-options=dbtype:sqlite3,database:/tmp/snmpsim.db,dbtable:snmprec
    Scanning "/usr/local/share/snmpsim/variation" directory for variation modules... sql module loaded
    SNMP version 2c
    Community name: public
    Querying UDP/IPv4 agent at demo.snmplabs.com:161
    Initializing variation module:
        sql...OK
    Shutting down variation modules:
        sql...OK
    OIDs dumped: 45, elapsed: 0.21 sec, rate: 213.00 OIDs/sec

By this point you'd get the *data/sql.snmprec* file where *sql* module
is configured for OID subtree (taken from *--start-oid* parameter):

.. code-block:: bash

    $ cat data/sql.snmprec
    1.3.6.1.2.1.2.2|:sql|snmprec

and SQLite database */tmp/snmpsim.db* having SQL table "snmprec" with the
following contents:

.. code-block:: bash

    $ sqlite3 /tmp/snmpsim.db
    SQLite version 3.7.5
    sqlite> .schema snmprec
    CREATE TABLE snmprec (oid text, tag text, value text, maxaccess text);
    sqlite> select * from snmprec limit 1;
             1.         3.         6.         1.         2.         1.
    2.         2.         1.         1.         1|2|1|read-write

.. note::

    The OID is formatted in a way that each sub-oid is left-padded with
    up to 8 spaces (must be 10 chars in total) to make the ordering work
    properly with standard SQL sorting.

The following :ref:`snmprec.py <snmprec.py>` call push snapshots into
MySQL database using native MySQL's Connector/Python driver:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --output-file=data/sql.snmprec \
      --variation-module=sql \
      --variation-module-options=dbtype:mysql.connector,host:127.0.0.1, \
    port:3306,user:snmpsim,password:snmpsim,database:snmpsim

The above code assumes that you have the
`MySQL Connector/Python driver <http://dev.mysql.com/doc/refman/5.5/en/connector-python.html>`_
installed on the recording machine and a MySQL server running at
127.0.0.1 with MySQL user/password snmpsim/snmpsim having sufficient permissions
for creating new tables.

Another variation of MySQL server installation setup on a UNIX system employs
UNIX domain socket for client-server communication. In that case the following
command-line for :ref:`snmprec.py <snmprec.py>` might work:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --output-file=data/sql.snmprec \
      --variation-module=sql
      --variation-module-options=dbtype:mysql.connector,unix_socket: \
      /var/run/mysql/mysql.sock,user:snmpsim,password:snmpsim,database:snmpsim

Alternatively, the `MySQL for Python <https://sourceforge.net/projects/mysql-python/>`_
package could be used for SNMP Simulator's MySQL connection:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --output-file=data/sql.snmprec \
      --variation-module=sql \
      --variation-module-options=dbtype:MySQLdb,host:127.0.0.1,port:3306, \
    user:snmpsim,passwd:snmpsim,db:snmpsim

Similar call but with the `PostgreSQL <http://www.postgresql.org/>`_ DB
as a backend data store:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --output-file=data/sql.snmprec \
      --variation-module=sql \
      --variation-module-options=dbtype:psycopg2,database:snmpsim,user:snmpsim, \
    password:snmpsim,dbtable:snmprec

With the example above, the assumption is that you have the
`Psycopg <http://initd.org/psycopg/>`_  module installed, PostgreSQL
server running locally (accessed through default UNIX domain socket),
DB user/password are snmpsim/snmpsim and this user has
sufficient permissions to create new database tables (snmprec table will
be created).

When *sql* variation module is invoked in :ref:`simulaiton <variate-sql>`
context, it can read, create and modify individual rows in the SQL database
we just created. You could also modify the contents of such SQL tables,
create SQL triggers to react to certain changes elsewhere.

.. _record-redis:

Redis module
------------

The *redis* module can record one or more snapshots of SNMP agent's set of
Managed Objects and store it in `Redis key-value store <http://redis.io>`_.
Recorded snapshots could then be replayed by *redis* module running
in :ref:`variation mode <variate-redis>`.

Redis database schema and module configuration parameters explained
on the :ref:`variation <variate-redis>` page is also applicable to
the recording mode.

The *redis* module supports the following comma-separated *key:value*
options whilst running in recording mode:

* *host* - Redis hostname or IP address.
* *port* - Redis TCP port the server is listening on.
* *unix_socket* - UNIX domain socket Redis server is listening on.
* *db* - Redis database number.
* *password* - Redis database admission password.
* *key-spaces-id* - key spaces ID to use for recording a single or a
  series of snapshots
* *iterations* - number of recording cycles to run over the same
  portion of SNMP agent MIB. There's no point in values
  beyond 2 for purposes of modelling approximation function.
  Default is 1.
* *period* - Agent walk period in seconds. Default is 10 seconds.
* *evalsha* - Redis server side `Lua script <http://redis.io/commands#scripting>`_
  to use for storing oid-value pairs in Redis. If this option is not given,
  bare Redis SET commands will be used instead.

Examples
++++++++

Make the *redis* module for recording five snapshots of a demo
SNMP Agent:

.. code-block:: bash

    $ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com \
      --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 \
      --output-file=data/redis.snmprec \
      --variation-module=redis \
      --variation-module-options=host:127.0.0.1,port:6379,db:0,key-spaces-id:1111, \
      iterations:5,period:30
    Scanning "variation" directory for variation modules...
    Variation module "redis" loaded
    SNMP version 2c, Community name: public
    Querying UDP/IPv4 agent at 195.218.195.228:161
    Initializing variation module...
    redis: using key-spaces-id 1111
    Variation module "redis" initialization OK
    Sending initial GETNEXT request....
    redis: done with key-space 0000001116
    redis: 4 iterations remaining
    85 OIDs dumped, waiting 30.00 sec(s)...
    redis: done with key-space 0000001115
    redis: 3 iterations remaining
    171 OIDs dumped, waiting 30.00 sec(s)...
    redis: done with key-space 0000001114
    redis: 2 iterations remaining
    257 OIDs dumped, waiting 30.00 sec(s)...
    redis: done with key-space 0000001113
    redis: 1 iterations remaining
    343 OIDs dumped, waiting 30.00 sec(s)...
    redis: done with key-space 0000001112
    redis: 0 iterations remaining
    Shutting down variation module redis...
    Variation module redis shutdown OK
    OIDs dumped: 603, elapsed: 329.22 sec, rate: 0.00 OIDs/sec

By this point you'd get the *data/redis.snmprec* file where *redis* module
is configured for OID subtree (taken from the *--start-oid* parameter):

.. code-block:: bash

    $ cat data/redis.snmprec
    1.3.6|:redis|period=30.00,key-spaces-id=1111

When *redis* variation module is invoked in the :ref:`variation context <variate-redis>`,
it can read, create and modify individual OID-value pairs in Redis database we've just
created.
