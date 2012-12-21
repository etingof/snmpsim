
SNMP Simulator
--------------
                                      Simulations are like miniskirts, 
                                      they show a lot and hide the essentials.
                                                         -- Hubert Kirrman

This software is intended for testing SNMP Managers against a large number
of SNMP Agents that represent a potentially very large network populated 
with different kinds of SNMP-capable devices.

Typical use case for this software starts with recording a snapshot of 
SNMP objects of donor Agents into text files using "snmprec" tool. 
Another option is to generate snapshots directly from MIB files with 
"mib2dev" tool. The latter appears useful whenever you do not posess 
a physical donor device. Then Simulator daemon would be run over the 
snapshots so that it could respond to SNMP queries in the same way as 
donor SNMP Agents did at the time of recording.

Technically, SNMP Simulator is a multi-context SNMP Agent. That means that
it handles multiple sets of Managed Object all at once. Each device is
simulated within a dedicated SNMP context.

SNMPv3 Manager talking to Simulator has to specify SNMP context name in
queries, while SNMPv1/v2c Manager can use specific SNMP community name
(logically bound to SNMP context) to access particular set of Managed
Objects.

It is also possible with the SNMP Simulator software to vary responses 
based on Manager's transport address, not only SNMPv3 context or SNMPv1/v2c 
community names.

Current Simulator version supports trivial SNMP SET operations in volatile
mode meaning that all previously SET values are lost upon daemon restart. 

The Simulator software is fully free and open source. It's written from
ground-up in an easy to learn and high-level scripting language called
Python. Everyone is welcome to modify Simulator in any way to best suite
their needs (note a [very permissive] BSD License is protecting Simulator).
If you'd rather would like us customizing or developing particular
Simulator feature for you, please let us know the details. 

Producing SNMP snapshots
------------------------

Primary method of recording an SNMP snapshot is to run snmprec tool against
your donor device. This tool will execute a series of SNMP GETNEXT queries
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

Valid tag values and their corresponding ASN.1/SNMP types are:

* Integer32         - 2
* OCTET STRING      - 4
* NULL              - 5
* OBJECT IDENTIFIER - 6
* IpAddress         - 64
* Counter32         - 65
* Gauge32           - 66
* TimeTicks         - 67
* Opaque            - 68
* Counter64         - 70

No other information or comments is allowed in the device file.

Device file recording would look like this:

$ snmprec.py  -h
Usage: snmprec.py [--help] [--debug=<category>] [--quiet] [--version=<1|2c|3>] [--community=<string>] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-auth-proto=<SHA|MD5>] [--v3-priv-proto=<3DES|AES256|DES|AES|AES128|AES192>] [--context=<string>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--start-oid=<OID>] [--stop-oid=<OID>] [--output-file=<filename>]
$
$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 --start-oid=1.3.6.1.2.1.2.1.0 --stop-oid=1.3.6.1.2.1.5  --output-file=devices/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
SNMP version 1
Community name: public
OIDs dumped: 304, elapsed: 1.94 sec, rate: 157.00 OIDs/sec
$
$ ls -l devices/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
-rw-r--r-- 1 ilya users 16252 Oct 26 14:49 devices/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec
$
$ head devices/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
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

Another way to produce device files is to run the mib2dev.py tool against
virtually any MIB file. With that method you do not have to have a donor
device and the values, that are normally returned by a donor device, will
instead be chosen randomly.

Keep in mind that you may run into either of two issues with these randomly
chosen values:

1. Some MIB data suggest certain correlation between formally unrelated
   pieces of information. Such relationships may be described informally,
   e.g. in natural language in the Description field. The automated
   values generation procedure has no chance to assure proper correlations,
   in that case the overall snapshot may appear inconsistent.

2. Some data types specified in the MIB may impose certain restrictions on
   the type instance values. For example an integer-typed Managed Object
   may be allowed to be either 0 or 12. If a guessed value turns out to be 2,
   it will be incompatible with this type. While it is possible to introspect
   type objects and generate a compliant value, the mib2dev.py tool does
   not do that [yet]. A non-compliant value will result an exception on
   MIB node instantiation. In that case the mib2dev.py script will revert
   to an interactive mode and ask you for a compliant value.

On the bright side, the mib2dev.py tool will respect Managed Object type
(e.g type associated with the OIDs), and produce valid indices for the MIB
tables.

Device file generation from a MIB file would look like this:

$ mib2dev.py 
Usage: mib2dev.py [--help] [--debug=<category>] [--quiet] [--pysnmp-mib-dir=<path>] [--mib-module=<name>] [--start-oid=<OID>] [--stop-oid=<OID>] [--manual-values] [--output-file=<filename>] [--string-pool=<words>] [--integer32-range=<min,max>]

Please note that to run mib2dev.py you would first have to convert an ASN.1
(e.g. text) MIB into a pysnmp module (with the libsmi2pysnmp tool shipped
with pysnmp disitribution).

Assuming we have the IF-MIB.py module in the pysnmp search path, run:

$ mib2dev.py --mib-module=IF-MIB 
# MIB module: IF-MIB
1.3.6.1.2.1.2.1.0|2|3
1.3.6.1.2.1.2.2.1.1.2|2|4
1.3.6.1.2.1.2.2.1.2.2|4|whisky au juge blond qui
1.3.6.1.2.1.2.2.1.3.2|2|4
1.3.6.1.2.1.2.2.1.4.2|2|3
1.3.6.1.2.1.2.2.1.5.2|66|1453149645
1.3.6.1.2.1.2.2.1.6.2|4|Portez ce vieux whisky
1.3.6.1.2.1.2.2.1.7.2|2|2
1.3.6.1.2.1.2.2.1.8.2|2|1
1.3.6.1.2.1.2.2.1.9.2|67|3622365885
1.3.6.1.2.1.2.2.1.10.2|65|1132976988
1.3.6.1.2.1.2.2.1.11.2|65|645067793
1.3.6.1.2.1.2.2.1.12.2|65|29258291
1.3.6.1.2.1.2.2.1.13.2|65|2267341229
1.3.6.1.2.1.2.2.1.14.2|65|3666596422
1.3.6.1.2.1.2.2.1.15.2|65|1846597313
1.3.6.1.2.1.2.2.1.16.2|65|1260601176
1.3.6.1.2.1.2.2.1.17.2|65|1631945174
1.3.6.1.2.1.2.2.1.18.2|65|499457590
1.3.6.1.2.1.2.2.1.19.2|65|278923014
1.3.6.1.2.1.2.2.1.20.2|65|3153307863
1.3.6.1.2.1.2.2.1.21.2|66|1395745280
1.3.6.1.2.1.2.2.1.22.2|6|1.3.6.1.3.99.148.60.97.205.134.179
# End of SNMPv2-SMI, 23 OID(s) dumped

One of the useful options are the --string-pool and --integer32-ranges. They
let you specify an alternative set of words and integer values ranges
to be used in random values generation.

Finally, you could always modify your device files with a text editor.

Simulating SNMP Agents
----------------------

Your collection of device files should look like this:

$ find devices
devices
devices/linux
devices/linux/1.3.6.1.2.1
devices/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec
devices/linux/1.3.6.1.2.1/127.0.0.1@public.dbm
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
Usage: snmpsimd.py [--help] [--debug=<category>] [--device-dir=<dir>] [--force-index-rebuild] [--validate-device-data] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--v2c-arch] [--v3-only] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-auth-proto=<SHA|NONE|MD5>] [--v3-priv-key=<key>] [--v3-priv-proto=<3DES|AES256|NONE|DES|AES|AES128|AES192>]

Running Simulator:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161 --agent-udpv6-endpoint='[::1]:1161' --agent-unix-endpoint=/tmp/snmpsimd.socket
Index ./devices/linux/1.3.6.1.2.1/127.0.0.1@public.dbm out of date
Indexing device file ./devices/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec...
...303 entries indexed
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Device file ./devices/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: @linux/1.3.6.1.2.1/127.0.0.1@public
SNMPv3 context name: 6d42b10f70ddb49c6be1d27f5ce2239e
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Device file ./devices/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.dump, dbhash-indexed, closed
SNMPv1/2c community name: @3com/switch8800/1.3.6.1.4.1/172.17.1.22@public
SNMPv3 context name: 1a80634d11a76ee4e29b46bc8085d871

SNMPv3 credentials:
Username: simulator
Authentication key: auctoritas
Authentication protocol: MD5
Encryption (privacy) key: privatus
Encryption protocol: DES

Listening at:
  UDP/IPv4 endpoint 127.0.0.1:1161, transport ID 1.3.6.1.6.1.1.0
  UDP/IPv6 endpoint [::1]:1161, transport ID 1.3.6.1.2.1.100.1.2.0
  UNIX domain endpoint /tmp/snmpsimd.socket, transport ID 1.3.6.1.2.1.100.1.13.0

Please note that multiple transports are supported in Simulator version 0.1.4
and later.  An unprivileged port is chosen in this example to avoid running
as root.

At this point you can run you favorite SNMP Manager to talk to either
of the two simulated devices through whatever transport you prefer.
For instance, to talk to simulated Linux box over SNMP v2 through
UDP over IPv4 run:

$ snmpwalk -On -v2c -c '@linux/1.3.6.1.2.1/127.0.0.1@public' localhost:1161 .1.3.6
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

Listing simulated devices
-------------------------

When simulating a large pool of devices or if your Simulator runs on a
distant machine, it is convenient to have a directory of all simulated
devices and their community/context names. Simulator maintains this
information within its internal, dedicated SNMP context 'index':

$ snmpwalk -On -v2c -c index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./devices/linux/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "devices/linux/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

or

$ snmpwalk -O n -l authPriv -u simulator -A auctoritas -X privatus -n index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./devices/linux/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "devices/linux/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

Where first column holds device file path, second - community string, and 
third - SNMPv3 context name.

Transport address based simulation
----------------------------------

Sometimes Managers can't easily change community name to address particular
simulated device instance as mention in the previous section. Or it may be
useful to present the same simulated device to different SNMP Managers
differently.

When running in --v2c-arch mode, Simulator (version 0.1.4 and later) would
attempt to find device file to fullfill a request by probing files by paths
constructed from pieces of request data. This path construction rules are
as follows:

<community> / <transport-ID> / <source-address> .snmprec
<community> / <transport-ID> .snmprec
<community> .snmprec

In other words, Simulator first tries to take community name (which
by the way may be an empty string), destination and source addresses
into account. If that does not match any existing file, the next probe
would use community name and destination address. The last resort is to
probe files by just community name, as described in previous chapters.

Transport ID is an OID that also identifies local transport endpoint (e.g.
protocol, local address and port Simulator is listening on). It is reported
by the Simulator on startup for each endpoint it is listening on.

When mapping source-address into a file, the following transformation
rules apply:

UDP/IPv4:
  192.168.1.1               -> 192.168.1.1
UDP/IPv6:
  fe80::12e:410f:40d1:2d13' -> fe80__12e_410f_40d1_2d13
UNIX local domain sockets:
  /tmp/snmpmanager.FAB24243 -> snmpmanager.FAB24243

For example, to make Simulator reporting from particular file to
a Manager at 192.168.1.10 whenever community name "public" is used and
queries are sent to Simulator over UDP/IPv4 to 192.168.1.1 interface
(which is reported by Simulator under transport ID 1.3.6.1.6.1.1.0),
device file public/1.3.6.1.6.1.1.0/192.168.1.10.snmprec whould be used
for building responses.

When Simulator is NOT running in --v2c-arch mode, e.g. SNMPv3 engine is
used, similar rules apply to SNMPv3 context name rather than to SNMPv1/2c
community name. In that case device file path construction would work
like this:

<context-name> / <transport-ID> / <source-address> .snmprec
<context-name> / <transport-ID> .snmprec
<context-name> .snmprec

For example, to make Simulator reporting from particular file to
a Manager at 192.168.1.10 whenever context-name is an empty string and
queries are sent to Simulator over UDP/IPv4 to 192.168.1.1 interface
(which is reported by Simulator under transport ID 1.3.6.1.6.1.1.0),
device file 1.3.6.1.6.1.1.0/192.168.1.10.snmprec whould be used
for building responses.

Sharing device files
--------------------

If a symbolic link is used as a device file, it would serve as an
alternative CommunityName/ContextName for the Managed Objects collection
read from the snapshot file being pointed to. Shared device files are
mentioned explicitly on Simulator startup:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161
Device file ./devices/public/1.3.6.1.6.1.1.0/127.0.0.1.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: public/1.3.6.1.6.1.1.0/127.0.0.1
SNMPv3 context name: 6d42b10f70ddb49c6be1d27f5ce2239e
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Shared device file ./devices/public/1.3.6.1.6.1.1.0/127.0.0.1.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: public/1.3.6.1.6.1.1.0/192.168.1.1
SNMPv3 context name: 1a80634d11a76ee4e29b46bc8085d871

SNMPv3 credentials:
Username: simulator
Authentication key: auctoritas
Authentication protocol: MD5
Encryption (privacy) key: privatus
Encryption protocol: DES

Listening at:
  UDP/IPv4 endpoint 127.0.0.1:1161, transport ID 1.3.6.1.6.1.1.0
^C

In the screenshot above, the public/1.3.6.1.6.1.1.0/127.0.0.1.snmprec
file is shared with the public/1.3.6.1.6.1.1.0/192.168.1.1.snmprec
symbolic link.

Now Managers can then use different credentials to access and modify the
same set of Managed Objects.

Simulation based on snmpwalk output
-----------------------------------

In some cases you may not be able to run snmprec.py against a donor 
device. For instance if you can't setup snmprec.py on a system from
where donor device is available or donor device is gone leaving you with
just Net-SNMP's snmpwalk dumps you have collected in the past.

Simulator provides limited support for snmpwalk-generated data files.
Just save snmpwalk output into a file with .snmpwalk suffix and put
it into Simulator data directory. Once Simulator finds and indexes
.snmpwalk files, it will report access information for them just
as it does for its native .snmprec files.

$ snmpwalk -v2c -c public -ObentU localhost 1.3.6 > myagent.snmpwalk

Make sure you get snmpwalk producing plain OIDs and values! By default
snmpwalk tries to beautify raw data from Agent with MIB information.
As beautified data may not contain OIDs and numeric values, it could
not be interpreted by the Simulator. Therefore always run snmpwalk
with the "-ObentU" parameters pack.

The .snmpwalk lines that can't be parsed by the Simulator will be skipped
and details reported to stdout for your further consideration. In particular,
current implementation does not cope well with multi-line strings
sometimes produced by snmpwalk. This may be improved in the future.

Simulation based on SAP dump files
----------------------------------

Another possible format for taking and storing SNMP snapshots is
SimpleSoft's Simple Agent Pro (http://www.smplsft.com/SimpleAgentPro.html).
Although we have neither seen any documentation on its data files format
nor ever owned or used Simple Agent Pro software, a sample data file
published on an Internet (http://tech.chickenandporn.com/2011/05/26/snmp-ping/)
reveals that SimpleAgentPro's file format is very similar to Net-SNMP's
snmpwalk. It essentially looks like snmpwalk output with different field
separators.

Be aware that Simulator might not support some parts of SimpleAgentPro
data files format so your milage may vary.

In case you store your SNMP snapshots archives in SimpleAgentPro's
data files and wish to use them with this Simulator, just put your
SimpleAgentPro-formatted SNMP snapshot information (excluding comments)
into text files having .sapwalk suffix and let Simulator find and index
them. Once completed, Simulator will report access information for them
just as it does for its native .snmprec files.

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
Written by Ilya Etingof <ilya@glas.net>, 2010-2012
