
SNMP Simulator
--------------

This software is intended for testing SNMP Managers against SNMP Agents
built into various network devices.

Typical use case for this software starts with recording a snapshot of
SNMP objects of a donor Agent into a text file using "snmprec" tool. Then
Simulator daemon would be run over the snapshots so that it could respond
to SNMP queries in the same way as donor SNMP Agent did at the time of
recording.

Technically, SNMP Simulator is a multi-context SNMP Agent. That means that
it handles multiple sets of Managed Object all at once. Each device is
simulated as a dedicated SNMP context.

SNMPv3 Manager talking to Simulator has to specify SNMP context name in
queries, while SNMPv1/v2c Manager can use specific SNMP community name
(logically bound to SNMP context) to access particular set of Managed Objects.

Recording SNMP snapshots
------------------------

To record an SNMP snapshot you need to run the snmprec tool against your
donor device. This tool will execute a series of SNMP GETNEXT queries
for a specified range of OIDs over a chosen SNMP protocol version and store
response data in a text file (AKA device file).

Device file format is optimized to be compact, human-readable and
inexpensive to parse. It's also important to store full and exact
response information in a most intact form. Here's an example device
file content:

1.3.6.1.2.1.1.1.0|4|Linux 2.6.25.5-smp SMP Tue Jun 19 14:58:11 CDT 2007 i686
1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.8072.3.2.10
1.3.6.1.2.1.1.3.0|67|233425120
1.3.6.1.2.1.2.2.1.6.2|4x|00127962f940
1.3.6.1.2.1.4.22.1.3.2.192.21.54.7|64x|c3dafe61

There is a pipe-separated triplet of OID-tag-value items where:

* OID is a dot-separated set of numbers.
* Tag is a BER-encoded ASN.1 tag. When value is hexified, an 'x' literal
  is appended.
* Value is either a printable string, a number or a hexifed value.

Device file recording would look like this:

$ snmprec.py  -h
Usage: snmprec.py [--help] [--debug=<category>] [--quiet] [--v1|2c|3] [--community=<string>] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-auth-proto=<MD5|SHA>] [--v3-priv-proto=<DES|AES>] [--context=<string>] [--agent-address=<IP>] [--agent-port] [--start-oid=<OID>] [--stop-oid=<OID>] [--output-file=<filename>]
$
$ snmprec.py --agent-address 127.0.0.1 --start-oid=1.3.6.1.2.1.2.1.0 --stop-oid=1.3.6.1.2.1.5  --output-file=devices/linux/slackware/1.3.6.1.2.1/127.0.0.1\@public.snmprec
OIDs dumped: 304, elapsed: 1.94 sec, rate: 157.00 OIDs/sec
$
$ ls -l devices/linux/slackware/1.3.6.1.2.1/127.0.0.1\@public.snmprec
-rw-r--r-- 1 ilya users 16252 Oct 26 14:49 devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.snmprec
$
$ head devices/linux/slackware/1.3.6.1.2.1/127.0.0.1\@public.snmprec
1.3.6.1.2.1.2.2.1.1.1|2|1
1.3.6.1.2.1.2.2.1.1.2|2|2
1.3.6.1.2.1.2.2.1.2.1|4|lo
1.3.6.1.2.1.2.2.1.2.2|4|eth0
1.3.6.1.2.1.2.2.1.3.1|2|24
1.3.6.1.2.1.2.2.1.3.2|2|6
1.3.6.1.2.1.2.2.1.4.1|2|16436
1.3.6.1.2.1.2.2.1.4.2|2|1500
1.3.6.1.2.1.2.2.1.5.1|66|10000000
1.3.6.1.2.1.2.2.1.5.2|66|100000000

There are no special requirements for device file name and location. Note,
that Simulator treats device file path as an SNMPv1/v2c community string
and its MD5 hash constitutes SNMPv3 context name.

Simulating SNMP Agents
----------------------

Your collection of device files should look like this:

$ find devices
devices
devices/linux
devices/linux/slackware
devices/linux/slackware/1.3.6.1.2.1
devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.snmprec
devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.dbm
devices/3com
devices/3com/switch8800
devices/3com/switch8800/1.3.6.1.4.1
devices/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.snmprec
devices/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.dbm
...

Notice those .dbm files -- they are by-OID indices of device files used
for fast lookup. These indices are created and updated automatically by
Simulator.

Getting help:

$ snmpsimd.py -h
Usage: snmpsimd.py [--help] [--debug=<category>] [--device-dir=<dir>] [--force-index-rebuild] [--validate-device-data] [--agent-address=<X.X.X.X>] [--agent-port=<port>] [--v2c-arch ] [--v3-only] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-priv-proto=<DES|AES>]

Running Simulator:

$ snmpsimd.py --agent-port=1161
Index ./devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.dbm out of date
Indexing device file ./devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.snmprec...
...303 entries indexed
Device file ./devices/linux/slackware/1.3.6.1.2.1/127.0.0.1@public.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: @linux/slackware/1.3.6.1.2.1/127.0.0.1@public
SNMPv3 context name: 6d42b10f70ddb49c6be1d27f5ce2239e

Device file ./devices/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.dump, dbhash-indexed, closed
SNMPv1/2c community name: @3com/switch8800/1.3.6.1.4.1/172.17.1.22@public
SNMPv3 context name: 1a80634d11a76ee4e29b46bc8085d871


SNMPv3 credentials:
Username: simulator
Authentication key: auctoritas
Encryption (privacy) key: privatus
Encryption protocol: (1, 3, 6, 1, 6, 3, 10, 1, 2, 2)

Listening at ('127.0.0.1', 1161)
...

An unprivileged port is chosen in this example to avoid running as root.

At this point you can run you favorite SNMP Manager to talk to either
of the two simulated devices. For instance, to talk to simulated Linux
box over SNMP v2:

$ snmpwalk -On -v2c -c '@linux/slackware/1.3.6.1.2.1/127.0.0.1@public' localhost:1161 .1.3.6
.1.3.6.1.2.1.2.2.1.1.1 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.1.2 = INTEGER: 2
.1.3.6.1.2.1.2.2.1.2.1 = STRING: lo
.1.3.6.1.2.1.2.2.1.2.2 = STRING: eth0
.1.3.6.1.2.1.2.2.1.3.1 = INTEGER: softwareLoopback(24)
.1.3.6.1.2.1.2.2.1.3.2 = INTEGER: ethernetCsmacd(6)
.1.3.6.1.2.1.2.2.1.4.1 = INTEGER: 16436
.1.3.6.1.2.1.2.2.1.4.2 = INTEGER: 1500
.1.3.6.1.2.1.2.2.1.5.1 = Gauge32: 10000000
.1.3.6.1.2.1.2.2.1.5.2 = Gauge32: 100000000
...

To walk simulated 3com switch over SNMPv3 we'd run:

$ snmpwalk -On -n 1a80634d11a76ee4e29b46bc8085d871 -u simulator -A auctoritas -X privatus -lauthPriv localhost:1161 .1.3.6
.1.3.6.1.2.1.1.1.0 = STRING: 3Com SuperStackII Switch 1000, SW Version:2.0
.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.3.1.8.3
.1.3.6.1.2.1.1.5.0 = STRING: Switch 1000
.1.3.6.1.2.1.1.6.0 = STRING: 3Com
.1.3.6.1.2.1.11.11.0 = Counter32: 0
.1.3.6.1.2.1.11.12.0 = Counter32: 0
.1.3.6.1.2.1.11.13.0 = Counter32: 1942
.1.3.6.1.2.1.11.16.0 = Counter32: 1384
.1.3.6.1.2.1.11.17.0 = Counter32: 0
.1.3.6.1.2.1.11.18.0 = Counter32: 0
...

Notice "-n <snmp-context>" parameter passed to snmpwalk to address particular
simulated device at Simulator.

When simulating a large pool of devices or if your Simulator runs on a
distant machine, it is convenient to have a directory of all simulated
devices and their community/context names. Simulator maintains this
information within its internal, dedicated SNMP context 'index':

$ snmpwalk -On -v2c -c index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./devices/linux/slackware/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "devices/linux/slackware/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

or

$ snmpwalk -O n -l authPriv -u simulator -A auctoritas -X privatus -n index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./devices/linux/slackware/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "devices/linux/slackware/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

Where first column holds device file path, second - community string, and 
third - SNMPv3 context name.

Performance improvement
-----------------------

The SNMPv3 architecture is inherently computationally heavy so Simulator
is somewhat slow. It can run faster if it would use a much lighter and
lower-level SNMPv2c architecture at the expense of not supporting v3
operations.

Use the --v2c-arch command line parameter to switch Simulator into SNMPv2c
(v1/v2c) operation mode.

When Simulator runs over thousands of device files, startup may take time
(tens of seconds). Most of it goes into configuring SNMPv1/v2c credentials
into SNMPv3 engine so startup time can be dramatically reduced by either
using --v2c-arch mode (as mentioned above) or by turning off SNMPv1/v2c
configuration at SNMPv3 engine with --v3-only command-line flag.

Installation
------------

The easiest way to download and install Simulator and its dependencies
is to use easy install:

$ easy_install snmpsim

Alternatively, you can download Simulator from SourceForge download servers:

https://sourceforge.net/projects/snmpsim

Then you can either install the scripts with standard 

$ python setup.py install

or simply run them off your home directory.

To run Simulator you need to have pysnmp-4 and pyasn1 packages
available on your system.

http://sourceforge.net/projects/pyasn1/
http://sourceforge.net/projects/pysnmp/

For secure SNMPv3 communication,PyCrypto should also be installed:

http://www.pycrypto.org

Getting help
------------

If something does not work as expected, please try browsing snmpsim
mailing list archives:

http://lists.sourceforge.net/mailman/listinfo/snmpsim-users

or post your question to <snmpsim-users@lists.sourceforge.net>

Feedback
--------

I'm interested in bug reports and fixes, suggestions and improvements.

I'm also interested in collecting SNMP snapshots taken from various
devices, so I'd eventually distribute it with the Simulator software
to let people test their SNMP Managers against many different devices.

If you wish to contribute such a snapshot - please, run snmprec for
your device and send me its output file. Make sure that your device
does not have any private information.

---
Written by Ilya Etingof <ilya@glas.net>, 2010-2011
