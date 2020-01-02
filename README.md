
SNMP Simulator
--------------
[![PyPI](https://img.shields.io/pypi/v/snmpsim.svg?maxAge=2592000)](https://pypi.org/project/snmpsim/)
[![Python Versions](https://img.shields.io/pypi/pyversions/snmpsim.svg)](https://pypi.org/project/snmpsim/)
[![Build status](https://travis-ci.org/etingof/snmpsim.svg?branch=master)](https://travis-ci.org/etingof/snmpsim)
[![GitHub license](https://img.shields.io/badge/license-BSD-blue.svg)](https://raw.githubusercontent.com/etingof/snmpsim/master/LICENSE.txt)

This is a pure-Python, open source and free implementation of SNMP agents simulator
distributed under 2-clause [BSD license](http://snmplabs.com/snmpsim/license.html).

Features
--------

* SNMPv1/v2c/v3 support
* SNMPv3 USM supports MD5/SHA/SHA224/SHA256/SHA384/SHA512 auth and
  DES/3DES/AES128/AES192/AES256 privacy crypto algorithms
* Runs over IPv4 and/or IPv6 transports
* Simulates many EngineID's, each with its own set of simulated objects
* Varies response based on SNMP Community, Context, source/destination addresses and ports
* Can gather and store snapshots of SNMP Agents for later simulation
* Can run simulation based on MIB files, snmpwalk and sapwalk output
* Can gather simulation data from network traffic or tcpdump snoops
* Can gather simulation data from external program invocation or a SQL database
* Can trigger SNMP TRAP/INFORMs on SET operations
* Capable to simultaneously simulate tens of thousands of Agents
* Offers REST API based [control plane](http://snmplabs.com/snmpsim-control-plane)
* Gathers and reports extensive activity metrics
* Pure-Python, easy to deploy and highly portable
* Can be extended by loadable Python snippets

Download
--------

SNMP simulator software is freely available for download from
[PyPI](https://pypi.org/project/snmpsim/) and
[project site](http://snmplabs.com/snmpsim/download.html).

Installation
------------

Just run:

```bash
$ pip install snmpsim
```

How to use SNMP simulator
-------------------------

Once installed, invoke `snmpsim-command-responder` and point it to a directory
with simulation data:

```
$ snmpsim-command-responder --data-dir=./data --agent-udpv4-endpoint=127.0.0.1:1024
```

Simulation data is stored in simple plaint-text files having OID|TYPE|VALUE
format:

```
$ cat ./data/public.snmprec
1.3.6.1.2.1.1.1.0|4|Linux 2.6.25.5-smp SMP Tue Jun 19 14:58:11 CDT 2007 i686
1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.8072.3.2.10
1.3.6.1.2.1.1.3.0|67|233425120
1.3.6.1.2.1.2.2.1.6.2|4x|00127962f940
1.3.6.1.2.1.4.22.1.3.2.192.21.54.7|64x|c3dafe61
...
```

Simulator maps query parameters like SNMP community names, SNMPv3 contexts or
IP addresses into data files.

You can immediately generate simulation data file by querying existing SNMP agent:

```
$ snmpsim-record-commands --agent-udpv4-endpoint=demo.snmplabs.com \
    --output-file=./data/public.snmprec
SNMP version 2c, Community name: public
Querying UDP/IPv4 agent at 195.218.195.228:161
Agent response timeout: 3.00 secs, retries: 3
Sending initial GETNEXT request for 1.3.6 (stop at <end-of-mib>)....
OIDs dumped: 182, elapsed: 11.97 sec, rate: 7.00 OIDs/sec, errors: 0
```

Alternatively, you could build simulation data from a MIB file:

```
$ snmpsim-record-mibs --output-file=./data/public.snmprec \
    --mib-module=IF-MIB
# MIB module: IF-MIB, from the beginning till the end
# Starting table IF-MIB::ifTable (1.3.6.1.2.1.2.2)
# Synthesizing row #1 of table 1.3.6.1.2.1.2.2.1
...
# Finished table 1.3.6.1.2.1.2.2.1 (10 rows)
# End of IF-MIB, 177 OID(s) dumped
```

Or even sniff on the wire, recover SNMP traffic there and build simulation
data from it.

Besides static files, SNMP simulator can be configured to call its plugin modules
for simulation data. We ship plugins to interface SQL and noSQL databases, file-based
key-value stores and other sources of information.

We maintain publicly available SNMP simulator instance at 
[demo.snmplabs.com](http://snmplabs.com/snmpsim/public-snmp-simulator.html). You are
welcome to query it as much as you wish.

Besides stand-alone deployment described above, third-party
[SNMP Simulator control plane](https://github.com/etingof/snmpsim-control-plane)
project offers REST API managed mass deployment of multiple `snmpsim-command-responder`
instances.

Documentation
-------------

Detailed information on SNMP simulator usage could be found at
[snmpsim site](http://snmplabs.com/snmpsim/).

Getting help
------------

If something does not work as expected,
[open an issue](https://github.com/etingof/snmpsim/issues) at GitHub or
post your question [on Stack Overflow](https://stackoverflow.com/questions/ask)
or try browsing snmpsim [mailing list archives](https://sourceforge.net/p/snmpsim/mailman/snmpsim-users/).

Feedback and collaboration
--------------------------

I'm interested in bug reports, fixes, suggestions and improvements. Your
pull requests are very welcome!

Copyright (c) 2010-2019, [Ilya Etingof](mailto:etingof@gmail.com). All rights reserved.
