
SNMP Simulator
--------------
[![PyPI](https://img.shields.io/pypi/v/snmpsim.svg?maxAge=2592000)](https://pypi.python.org/pypi/snmpsim)
[![Python Versions](https://img.shields.io/pypi/pyversions/snmpsim.svg)](https://pypi.python.org/pypi/snmpsim/)
[![Build status](https://travis-ci.org/etingof/snmpsim.svg?branch=master)](https://secure.travis-ci.org/etingof/snmpsim)
[![GitHub license](https://img.shields.io/badge/license-BSD-blue.svg)](https://raw.githubusercontent.com/etingof/snmpsim/master/LICENSE.txt)

This is a pure-Python, open source and free implementation of SNMP agents simulator
distributed under 2-clause [BSD license](http://pysnmp.sourceforge.net/license.html).

Features
--------

* Pure-Python, easy to deploy and highly portable
* SNMPv1/v2c/v3 support
* USM supports MD5/SHA auth and DES/AES/3DES/AES256 privacy
* Runs over IPv4 and/or IPv6 transports
* Simulates many EngineID's, each with its own set of simulated objects
* Varies response based on SNMP Community, Context, source/destination addresses and ports
* Can gather and store snapshots of SNMP Agents for later simulation
* Can run simulation based on MIB files, snmpwalk and sapwalk output
* Can gather simulation data from network traffic or tcpdump snoops
* Can gather simulation data from external program invocation or a SQL database
* Can trigger SNMP TRAP/INFORMs on SET operations
* Capable to simultaneously simulate tens of thousands of Agents
* Easy to extend by Python scripting


Download
--------

SNMP simulator software is freely available for download from [PyPI](https://pypi.python.org/pypi/snmpsim)
and [project site](http://snmpsim.sf.net/download.html).

Installation
------------

Just run:

```bash
$ pip install snmpsim
```

How to use SNMP simulator
-------------------------

Once installed, invoke snmpsimd.py and point it to a directory with simulation data:

```
$ snmpsimd.py --data-dir=./data --agent-udpv4-endpoint=127.0.0.1:1024
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
$ snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com --output-file=./data/public.snmprec
SNMP version 2c, Community name: public
Querying UDP/IPv4 agent at 195.218.195.228:161
Agent response timeout: 3.00 secs, retries: 3
Sending initial GETNEXT request for 1.3.6 (stop at <end-of-mib>)....
OIDs dumped: 182, elapsed: 11.97 sec, rate: 7.00 OIDs/sec, errors: 0
```

Alternatively, you could build simulation data from a MIB file:

```
$ mib2dev.py --output-file=./data/public.snmprec --mib-module=IF-MIB
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
[demo.snmplabs.com](http://snmpsim.sourceforge.net/public-snmp-simulator.html). You are
welcome to query it as much as you wish.

Documentation
-------------

Detailed information on SNMP simulator usage could be found at
[snmpsim site](http://snmpsim.sf.net/).

Getting help
------------

If something does not work as expected, try browsing
[mailing list archives](https://sourceforge.net/p/snmpsim/mailman/snmpsim-users/) or post
your question [to Stack Overflow](http://stackoverflow.com/questions/ask).

Feedback and collaboration
--------------------------

I'm interested in bug reports, fixes, suggestions and improvements. Your
pull requests are very welcome!

Copyright (c) 2010-2017, [Ilya Etingof](mailto:etingof@gmail.com). All rights reserved.
