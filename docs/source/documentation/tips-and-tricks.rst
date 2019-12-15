
Tips and tricks
===============

Here we have a handful of observations and advices based on user feedback
and field deployment.

.. _tips-multiple-instances:

Multiple instances
------------------

SNMP Simulator is designed to simulate tens of thousands of SNMP Agents
at once. However, it is more optimized for large number of simulated
devices than to high sustainability under high load.

The reason is that, internally, SNMP Simulator is a single-threaded
application meaning it can only process a single request
at once. On top of that, some variation modules may bring additional delay to
request processing what may cause subsequent requests to build up in
input queue and contribute to increasing latency.

A simple receipt aimed at maximizing throughput and minimizing latency is
to run multiple instances of the *snmpsim-command-responder* bound to distinct
IP interfaces or ports what effectively makes SNMP Simulator executing multiple
requests at once for as long as they are sent towards different
*snmpsim-command-responder* instances.

Here is how we invoke two *snmpsim-command-responder* instances on
different IP interfaces serving the same set of data files:

.. code-block:: bash

    # snmpsim-command-responder --agent-udpv4-endpoint=127.0.0.1 \
                  --agent-udpv4-endpoint=127.0.0.2 \
                  --transport-id-offset=1 \
                  --data-dir=/usr/local/share/snmpsim/data \
                  --cache-dir=/var/tmp/snmpsim-A/cache \
                  --process-user=nobody --process-group=nogroup \
                  --daemonize &&
    # snmpsim-command-responder --agent-udpv4-endpoint=127.0.0.3 \
                  --agent-udpv4-endpoint=127.0.0.4 \
                  --transport-id-offset=3 \
                  --data-dir=/usr/local/share/snmpsim/data \
                  --cache-dir=/var/tmp/snmpsim-B/cache \
                  --process-user=nobody --process-group=nogroup \
                  --daemonize &&

Several things to note here:

* The *snmpsim-command-responder* instances share common data directory
  however use their own, dedicated cache directories.

* Each *snmpsim-command-responder* instance is listening on multiple IP
  interfaces (for the purpose of
  :ref:`address-based <addressing-simulation-data>` simulation)

* The transport ID's are configured explicitly making the following
  *--data-dir* layout possible:

.. code-block:: bash

    $ tree data
      data
      |-- public
      |     |-- 1.3.6.1.6.1.1.1.snmprec
      |-- public
      |     |-- 1.3.6.1.6.1.1.2.snmprec
      |-- public
      |     |-- 1.3.6.1.6.1.1.3.snmprec
      |-- public
            |-- 1.3.6.1.6.1.1.4.snmprec

The end result is that each simulated Agent is available by a dedicated
IP address (represented by a transport ID) and common SNMPv1/v2c community
name *public*.

.. note::

    To make use of IP address based Agent addressing feature the *--v2c-arch*
    mode is used.

.. _tips-file-based-configuration:

File-based configuration
------------------------

The above setup can be scaled to as many IP interfaces as you can bring
up on your system. A really large number of IP interfaces might exceed
the length of the command-line. In that case it's advised to use the
*--args-from-file=<file>*; option to pass local IP addresses
for Simulator to listen on.

.. code-block:: bash

    # head ips.txt
    --agent-udpv4-endpoint=127.0.0.1:161
    --agent-udpv4-endpoint=127.0.0.2:161
    --agent-udpv4-endpoint=127.0.0.3:161
    ...
    --agent-udpv4-endpoint=127.0.1.254:161
    # snmpsim-command-responder --args-from-file=ips.txt \
          --data-dir=/usr/local/share/snmpsim/data \
          --v2c-arch \
          --process-user=nobody --process-group=nogroup \
          --daemonize &

.. note::

    Other parameters can also be present in the file passed to Simulator with
    the *--args-from-file* option.

For the :ref:`address-based <addressing-simulation-data>` simulation it makes
to design your *--data-dir* layout matching transport ID's of the addresses
listed in the *ips.txt* file as shown above.

.. _tips-listing-simulated-devices:

Listing simulated agents
------------------------

When simulating a large pool of devices or if your Simulator runs on a
distant machine, it is convenient to have a directory of all simulated
devices and their community/context names. Simulator maintains this
information within its internal, dedicated SNMP context 'index':

.. code-block:: bash

    $ snmpwalk -On -v2c -c index localhost:1161 .1.3.6
    .1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./data/127.0.0.1@public.snmprec"
    .1.3.6.1.4.1.20408.999.1.2.1 = STRING: "data/127.0.0.1@public"
    .1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

or

.. code-block:: bash

    $ snmpwalk -O n -l authPriv -u simulator -A auctoritas -X privatus
    -n index localhost:1161 .1.3.6
    .1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./data/127.0.0.1@public.snmprec"
    .1.3.6.1.4.1.20408.999.1.2.1 = STRING: "data/127.0.0.1@public"
    .1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

Where first column holds device file path, second - community string, and
third - SNMPv3 context name.

.. _tips-faster-response:

Faster operation
----------------

The SNMPv3 architecture is inherently computationally heavy what makes SNMPv3
operations slower that SNMPv1/v2c ones. The SNMP Simulator can run
faster when it uses a much lighter and lower-level SNMPv1/v2c architecture
at the expense of not supporting v3 operations.

Invoke *snmpsim-command-responder-lite* tool to leverage the lightweight
implementation.

.. _tips-quick-startup:

Quicker startup
---------------

When Simulator runs over thousands of device files, startup may take time
(tens of seconds). Most of it goes into configuring SNMPv1/v2c credentials
into SNMPv3 engine so startup time can be dramatically reduced by either
using the lite version of command responder tool or by turning off
SNMPv1/v2c configuration at SNMPv3 engine with *--v3-only* command-line
flag of full version of command responder.
