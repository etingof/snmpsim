
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

Even more powerful is Simulator's ability to gateway SNMP queries to
its extension (also called "variation" modules). Once a variation module
is invoked by Simulator core, it is expected to return a well-formed
variable-binding sequence to be put into Simulator's response message.

Simulator is shipped with a collecton of factory-built variation modules 
including those suitable for external process invocation, SNMPTRAP/INFORM 
originator and SQL database adapter. Users of the Simulator software are
welcome to develop their own variation modules if stock ones appears
insufficient.

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
response data in a text file.

Data file format is optimized to be compact, human-readable and
inexpensive to parse. It's also important to store full and exact
response information in a most intact form. Here's an example data 
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

No other information or comments is allowed in the data file.

Device file recording would look like this:

$ snmprec.py  -h
Usage: snmprec.py [--help] [--debug=<category>] [--quiet] [--version=<1|2c|3>] [--community=<string>] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-auth-proto=<SHA|MD5>] [--v3-priv-proto=<3DES|AES256|DES|AES|AES128|AES192>] [--context=<string>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--start-oid=<OID>] [--stop-oid=<OID>] [--output-file=<filename>]
$
$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 --start-oid=1.3.6.1.2.1.2.1.0 --stop-oid=1.3.6.1.2.1.5  --output-file=snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
SNMP version 1
Community name: public
OIDs dumped: 304, elapsed: 1.94 sec, rate: 157.00 OIDs/sec
$
$ ls -l snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
-rw-r--r-- 1 ilya users 16252 Oct 26 14:49 snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec
$
$ head snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1\@public.snmprec
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

There are no special requirements for data file name and location. Note,
that Simulator treats data file path as an SNMPv1/v2c community string
and its MD5 hash constitutes SNMPv3 context name.

Another way to produce data files is to run the mib2dev.py tool against
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

Finally, you could always modify your data files with a text editor.

Simulating SNMP Agents
----------------------

Your collection of data files should look like this:

$ find snmpsim/data
devices
snmpsim/data/linux
snmpsim/data/linux/1.3.6.1.2.1
snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec
snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.dbm
snmpsim/data/3com
snmpsim/data/3com/switch8800
snmpsim/data/3com/switch8800/1.3.6.1.4.1
snmpsim/data/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.snmprec
snmpsim/data/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.dbm
...

Notice those .dbm files -- they are by-OID indices of data files used
for fast lookup. These indices are created and updated automatically by
Simulator.

Getting help:

$ snmpsimd.py -h
Usage: snmpsimd.py [--help] [--version ] [--debug=<category>] [--data-dir=<dir>] [--force-index-rebuild] [--validate-data] [--variation-modules-dir=<dir>] [--variation-module-options=<module[=alias][:args]>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--v2c-arch] [--v3-only] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-auth-proto=<SHA|NONE|MD5>] [--v3-priv-key=<key>] [--v3-priv-proto=<3DES|AES256|NONE|DES|AES|AES128|AES192>]

Running Simulator:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161 --agent-udpv6-endpoint='[::1]:1161' --agent-unix-endpoint=/tmp/snmpsimd.socket
Index ./snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.dbm out of date
Indexing data file ./snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec...
...303 entries indexed
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Device file ./snmpsim/data/linux/1.3.6.1.2.1/127.0.0.1@public.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: @linux/1.3.6.1.2.1/127.0.0.1@public
SNMPv3 context name: 6d42b10f70ddb49c6be1d27f5ce2239e
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Device file ./snmpsim/data/3com/switch8800/1.3.6.1.4.1/172.17.1.22@public.dump, dbhash-indexed, closed
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
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./snmpsim/data/linux/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "snmpsim/data/linux/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

or

$ snmpwalk -O n -l authPriv -u simulator -A auctoritas -X privatus -n index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "./snmpsim/data/linux/1.3.6.1.2.1.1.1/127.0.0.1@public.snmprec"
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "snmpsim/data/linux/1.3.6.1.2.1.1.1/127.0.0.1@public"
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "9535d96c66759362b3521f4e273fc749"

Where first column holds data file path, second - community string, and 
third - SNMPv3 context name.

Transport address based simulation
----------------------------------

Sometimes Managers can't easily change community name to address particular
simulated device instance as mention in the previous section. Or it may be
useful to present the same simulated device to different SNMP Managers
differently.

When running in --v2c-arch mode, Simulator (version 0.1.4 and later) would
attempt to find data file to fullfill a request by probing files by paths
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
data file public/1.3.6.1.6.1.1.0/192.168.1.10.snmprec whould be used
for building responses.

When Simulator is NOT running in --v2c-arch mode, e.g. SNMPv3 engine is
used, similar rules apply to SNMPv3 context name rather than to SNMPv1/2c
community name. In that case data file path construction would work
like this:

<context-name> / <transport-ID> / <source-address> .snmprec
<context-name> / <transport-ID> .snmprec
<context-name> .snmprec

For example, to make Simulator reporting from particular file to
a Manager at 192.168.1.10 whenever context-name is an empty string and
queries are sent to Simulator over UDP/IPv4 to 192.168.1.1 interface
(which is reported by Simulator under transport ID 1.3.6.1.6.1.1.0),
data file 1.3.6.1.6.1.1.0/192.168.1.10.snmprec whould be used
for building responses.

Sharing data files
------------------

If a symbolic link is used as a data file, it would serve as an
alternative CommunityName/ContextName for the Managed Objects collection
read from the snapshot file being pointed to. Shared data files are
mentioned explicitly on Simulator startup:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161
Device file ./snmpsim/data/public/1.3.6.1.6.1.1.0/127.0.0.1.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: public/1.3.6.1.6.1.1.0/127.0.0.1
SNMPv3 context name: 6d42b10f70ddb49c6be1d27f5ce2239e
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Shared data file ./snmpsim/data/public/1.3.6.1.6.1.1.0/127.0.0.1.snmprec, dbhash-indexed, closed
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

Using variation modules
-----------------------

Without variation modules, simulated SNMP Agents are always static
in terms of data returned to SNMP Managers. They are also read-only.
By configuring particular OIDs or whole subtrees to be gatewayed to
variation modules allows you to make returned data changing in time.

Another way of using variation modules is to gather data from some
external source such as an SQL database or executed process or distant
web-service.

It's also possible to modify simulated values through SNMP SET operation
and store modified values in a database so they will persist over Simulator
restarts.

Variation modules may be used for triggering events at other systems. For
instance stock "notification" module will send SNMP TRAP/IMFORM messages
to pre-configured SNMP Managers on SNMP SET request arrival to Simulator.

Finally, variation module API let you develop your own code in Python
to fulfill your special needs and use your variation module with stock
Simulator.

Here's the current list of variation modules supplied with Simulator:

* counter - produces a non-decreasing sequence of integers over time
* gauge - produces a random number in specified range
* notification - sends SNMP TRAP/INFORM messages to disitant SNMP entity
* volatilecache - accepts and stores (in memory) SNMP var-binds through SNMP SET
* involatilecache - accepts and stores (in file) SNMP var-binds through
                    SNMP SET 
* sql - reads/writes var-binds from/to a SQL database
* delay - delays SNMP response by specified or random time
* error - flag errors in SNMP response PDU
* subprocess - executes external process and puts its stdout values into
               response

To make use of a variation module you will have to *edit* existing
or create a new data file adding reference to a variation module into the
"tag" field.

Consider .snmprec file format is a sequence of lines in the following
format:

<OID>|<TAG>|<VALUE>

whereas TAG field complies to its own format:

TAG-ID[:MODULE-ID]

For example, the following .snmprec file contents will invoke the
"volatilecache" module:

1.3.6.1.2.1.1.1.0|4:volatilecache|I'm a string, please modify me
1.3.6.1.2.1.1.3.0|2:volatilecache|42

and cast its returned values into ASN.1 OCTET STRING (4) and INTEGER (2)
respectively.

Whenever a subtree is gatewayed to a variation module, TAG-ID part is left out
as there might be no single type for all values within a subtree. Thus the
empty TAG-ID sub-field serves as an indicator of a subtree:

For example, the following data file will serve all OIDs under 1.3.6.1.2.1.1
prefix to the "sql" variation module:

1.3.6.1.2.1.1|:sql|system

The value part is passed to variation module as-is. It is typically holds some
module-specific configuration or initialization values.

For example, the following .snmprec line invokes the "notification" variation
module instructing it to send SNMP INFORM message (triggered by SET message to
the 1.3.6.1.2.1.1.3.0 OID served by Simulator) to SNMP Manager at
127.0.01:162 over SNMPv3 with specific SNMP params:

1.3.6.1.2.1.1.3.0|67:notification|version=3,user=usr-md5-des,authkey=authkey1,privkey=privkey1,host=127.0.0.1,ntftype=inform,trapoid=1.3.6.1.6.3.1.1.5.2,value=123456

A small (but growing) collection of variation modules are shipped along with
Simulator and normally installed into the Python site-packages directory.
User can pass Simulator an alternative modules directory through its command
line.

Simulator will load and bootstrap all variation modules it finds. Some
modules can accept initialization parameters (like database connection
credentials) through Simulator's --variation-module-options command-line
parameter.

For example, the following Simulator invocation will configure its
"sql" variation module to use sqlite database (sqlite3 Python module)
and /var/tmp/system.db database file:

$ snmpsimd.py --variation-module-options=sql:sqlite3:/var/tmp/system.db

In case you are using multiple database connections or database types
all through the sql variation module, you could refer to each module instance
in .snmprec files through a so-called variation module alias.

The following command-line runs Simulator with two instances of the
"involatilecache" variation module (dbA & dbB) each instance using 
distinct database file for storing their persistent values:

$ snmpsimd.py --variation-module-options=involatilecache=dbA:/var/tmp/fileA.db --variation-module-options=involatilecache=dbB:/var/tmp/fileB.db

What follows is a brief description of some of the variation modules
included into the distribution.

Counter module
++++++++++++++

The counter module maintains and returns a never decreasing integer value
(except for the case of overflow) changing in time in accordance with 
user-defined rules. This module is per-OID stateful and configurable.

The counter module accepts the following comma-separated key=value parameters
in .snmprec value field:

  min - the minimum value ever stored and returned by this module.
        Default is 0.
  max - the maximum value ever stored and returned by this module.
        Default is 2**32 (0xFFFFFFFF).
  wrap - if zero, generated value will freeze when reaching 'max'. Otherwise
         generated value is reset to 'min'.
  function - defines elapsed-time-to-generated-value relationship. Can be
             any of reasonably suitable mathematical function from the
             math module such as sin, log, pow etc. The only requirement
             is that used function accepts a single integer argument. 
             Default is x = f(x).
  rate - elapsed time scaler. Default is 1.
  scale - function value scaler. Default is 1.
  offset - constant value by which the return value increases on each
           invocation. Default is 0.
  deviation - random deviation maximum. Default is 0 which means no
              deviation.

This module generates values by execution of the following formula:

  v = abs(function(UPTIME * rate) * scale + offset + RAND(0, deviation)

Here's an example counter module use in a .snmprec file:

  1.3.6.1.2.1.2.2.1.13.1|65:counter|max=100,scale=0.6,deviation=1,function=cos

Gauge module
++++++++++++

The gauge module maintains and returns an integer value changing in time
in accordance with user-defined rules. This module is per-OID stateful and
configurable.

The gauge module accepts the following comma-separated key=value parameters
in .snmprec value field:

  min - the minimum value ever stored and returned by this module.
        Default is 0.
  max - the maximum value ever stored and returned by this module.
        Default is 2**32 (0xFFFFFFFF).
  function - defines elapsed-time-to-generated-value relationship. Can be
             any of reasonably suitable mathematical function from the
             math module such as sin, log, pow etc. The only requirement
             is that used function accepts a single integer argument. 
             Default is x = f(x).
  rate - elapsed time scaler. Default is 1.
  scale - function value scaler. Default is 1.
  offset - constant value by which the return value increases on each
           invocation. Default is 0.
  deviation - random deviation minimum and maximum. Default is 0 which means no
              deviation.

This module generates values by execution of the following formula:

  v = function(UPTIME * rate) * scale + offset + RAND(-deviation, deviation)

Here's an example gauge module use in a .snmprec file:

  1.3.6.1.2.1.2.2.1.21.1|66:gauge|function=sin,scale=100,deviation=0.5

Delay module
++++++++++++

The delay module postpones SNMP request processing for specified number of
milliseconds.

Delay module accepts the following comma-separated key=value parameters
in .snmprec value field:

  value - holds the var-bind value to be included into SNMP response.
          In case of a string value containing commas, use 'hexvalue'
          instead.
  hexvalue - holds the var-bind value as a sequence of ASCII codes in hex
             form. Before putting it into var-bind, hexvalue contents will
             be converted into ASCII text.
  wait - specifies for how many milliseconds to delay SNMP response.
         Default is 500ms.
  deviation - random delay deviation ranges. Default is 0 which means no
              deviation.

Here's an example delay module use in a .snmprec file:

1.3.6.1.2.1.2.2.1.3.1|2:delay|value=6,wait=100,deviation=200
1.3.6.1.2.1.2.2.1.4.1|2:delay|1500
1.3.6.1.2.1.2.2.1.6.1|4:delay|hexvalue=00127962f940,wait=800

The first entry makes Simulator responding with an integer value of 6 delayed
by 0.1sec +- 0.2 sec. Negative delays are casted into zeros. The second entry
is similar to the first one but uses delay module defaults. Finally, the last
entry takes shape of an OCTET STRING value '0:12:79:62:f9:40' delayed by
exactly 0.8 sec.

Keep in mind that since Simulator is a single-thread application,
any delayed response will delay all concurrent requests processing as well.

Error module
++++++++++++

The error module flags a configured error at SNMP response PDU.

Error module accepts the following comma-separated key=value parameters
in .snmprec value field:

  op - either of 'get', 'set' or 'any' values to indicate SNMP operation 
       that would trigger error response. Here 'get' also enables GETNEXT 
       and GETBULK operations. Default is 'any'.
  value - holds the var-bind value to be included into SNMP response.
          In case of a string value containing commas, use 'hexvalue'
          instead.
  hexvalue - holds the var-bind value as a sequence of ASCII codes in hex
             form. Before putting it into var-bind, hexvalue contents will
             be converted into ASCII text.
  status - specifies error to be flagged. The following errors are
           supported: 'generror', 'noaccess', 'wrongtype', 'wrongvalue',
           'nocreation', 'inconsistentvalue', 'resourceunavailable',
           'commitfailed', 'undofailed', 'authorizationerror',
           'notwritable', 'inconsistentname', 'nosuchobject',
           'nosuchinstance', 'endofmib'

Here's an example error module use in a .snmprec file:

1.3.6.1.2.1.2.2.1.1.1|2:error|op=get,status=authorizationError,value=1
1.3.6.1.2.1.2.2.1.2.1|4:error|op=set,status=commitfailed,hexvalue=00127962f940
1.3.6.1.2.1.2.2.1.6.1|4:error|status=noaccess

The first entry flags 'authorizationError' on GET* and no error
on SET. Second entry flags 'commitfailed' on SET but responds without errors
to GET*. Finally, third entry always flags 'noaccess' error.

Volatile Cache module
+++++++++++++++++++++

The volatile cache module lets you make particular OID at a .snmprec file
writable via SNMP SET operation. The new value will be stored in Simulator
process's memory and communicated back on SNMP GET/GETNEXT/GETBULK 
operations. Stored data will be lost upon Simulator restart.

The .snmprec value will be used as an initial value by the volatilecache
module.

Here's an example volatilecache module use in a .snmprec file:

1.3.6.1.2.1.1.3.0|2:volatilecache|42

In the above configuration, the initial value is 42 and can be modified by:

snmpset -v2c -c <commiunity> localhost 1.3.6.1.2.1.1.3.0 i 24

command (assuming correct community name and Simulator is running locally).

Involatile cache module
+++++++++++++++++++++++

The involatilecache module works similar to the volatilecache one, but
the involatile version has an ability of storing current values in a persistent
database.

Module invocation requires passing a name of a database file to be
created if not already exists:

$ snmpsimd.py --variation-module-options=involatilecache:/tmp/shelves.db

All modifed values will be kept and then subsequently used on a per-OID
basis in the specified file.

Subprocess module
+++++++++++++++++

The subprocess module can be used to execute an external program
passing it request data and using its stdout output as a response value.

Value part of .snmprec line should contain space-separated path
to external program executable followed by optional command-line
parameters.

SNMP request parameters could be passed to the program to be executed
by means of macro variables. With subprocess module, macro variables
names always carry '@' sign at front and back (e.g. @MACRO@).

Full list of supported macros follows:

  @DATAFILE@ - resolves into the .snmprec file selected by Simulator
               for serving current request
  @OID@ - resolves into an OID of .snmprec line selected for serving
          current request
  @TAG@ - resolves into the <tag> component of snmprec line selected for
          serving current request
  @ORIGOID@ - resolves into currenty processed var-bind OID
  @ORIGTAG@ - resolves into value type of currently processed var-bind
  @ORIGVALUE@ - resolves into value of currently processed var-bind
  @SETFLAG@ - resolves into '1' on SNMP SET, '0' otherwise
  @NEXTFLAG@ - resolves into '1' on SNMP GETNEXT/GETBULK, '0' otherwise
  @SUBTREEFLAG@ - resolves into '1' if the .snmprec file line selected
                  for processing current request serves a subtree of
                  OIDs rather than a single specific OID

Here's an example subprocess module use in a .snmprec file:

1.3.6.1.2.1.1.1.0|4:subprocess|echo SNMP Context is @DATAFILE@, received request for @ORIGOID@, matched @OID@, received tag/value "@ORIGTAG@"/"@ORIGVALUE@", would return value tagged @TAG@, SET request flag is @SETFLAG@, next flag is @NEXTFLAG@, subtree flag is @SUBTREEFLAG@
1.3.6.1.2.1.1.3.0|2:subprocess|date +%s

The first entry simply packs all current macro variables contents as a
response string my printing them to stdout with echo, second entry invokes
the UNIX date command instructing it to report elapsed UNIX epoch time.

Note .snmprec tag values -- executed program's stdout will be casted into
appropriate type depending of tag indication.

Notification module
+++++++++++++++++++

The notification module can send SNMP TRAP/INFORM notifications to
distant SNMP engines by way of serving SNMP request sent to Simulator.
In other words, SNMP message sent to Simulator can trigger sending
TRAP/INFORM message to pre-configured targets.

No new process execution is involved in the operations of this module,
it uses Simulator's SNMP engine for notification generation.

Notification module accepts the following comma-separated key=value parameters
in .snmprec value field:

  value - holds the var-bind value to be included into SNMP response
          message.
  op - either of 'get', 'set' or 'any' values to indicate SNMP operation that
       would trigger notification. Here 'get' also enables GETNEXT and GETBULK
       operations. Default is 'set'.
  version - SNMP version to use (1,2c,3).
  ntftype - indicates notification type. Either 'trap' or 'inform'.
  community - SNMP community name. For v1, v2c only. Default is 'public'.
  trapoid - SNMP TRAP PDU element. Default is coldStart.
  uptime - SNMP TRAP PDU element. Default is local SNMP engine uptime.
  agentaddress - SNMP TRAP PDU element. For v1 only. Default is local SNMP
                 engine address.
  enterprise - SNMP TRAP PDU element. For v1 only.
  user - USM username. For v3 only.
  authproto - USM auth protocol. For v3 only. Either 'md5' or 'sha'.
              Default is 'md5'.
  authkey - USM auth key. For v3 only.
  privproto - USM encryption protocol. For v3 only. Either 'des' or 'aes'.
              Default is 'des'.
  privkey - USM encryption key. For v3 only.
  proto - transport protocol. Either 'udp' or 'udp6'. Default is 'udp'.
  varbinds - a semicolon-separated list of OID:TAG:VALUE:OID:TAG:VALUE...
             of var-binds to add into SNMP TRAP PDU.
  host - hostname or network address to send notification to.
  port - UDP port to send notification to. Default is 162.

where <TAG> is a single character of:

  s: OctetString
  i: Integer32
  o: ObjectName
  a: IpAddress
  u: Unsigned32
  g: Gauge32
  t: TimeTicks
  b: Bits
  I: Counter64

For example, the following three .snmprec lines will send SNMP v1, v2c
and v3 notifications whenever Simulator is processing GET* and/or SET request
for configured OIDs:

1.3.6.1.2.1.1.1.0|4:notification|op=get,version=1,community=public,proto=udp,host=127.0.0.1,port=162,ntftype=trap,trapoid=1.3.6.1.4.1.20408.4.1.1.2.0.432,uptime=12345,agentaddress=127.0.0.1,enterprise=1.3.6.1.4.1.20408.4.1.1.2,varbinds=1.3.6.1.2.1.1.1.0:s:snmpsim agent:1.3.6.1.2.1.1.3.0:i:42,value=SNMPv1 trap sender
1.3.6.1.2.1.1.2.0|6:notification|op=set,version=2c,community=public,host=127.0.0.1,ntftype=trap,trapoid=1.3.6.1.6.3.1.1.5.1,varbinds=1.3.6.1.2.1.1.1.0:s:snmpsim agent:1.3.6.1.2.1.1.3.0:i:42,value=1.3.6.1.1.1
1.3.6.1.2.1.1.3.0|67:notification|version=3,user=usr-md5-des,authkey=authkey1,privkey=privkey1,host=127.0.0.1,ntftype=inform,trapoid=1.3.6.1.6.3.1.1.5.2,value=123456

Keep in mind that delivery status of INFORM notifications is not communicated
back to SNMP Manager working with Simulator.

SQL module
++++++++++

The sql module lets you keep subtrees of OIDs and their values in a relational
database. All SNMP operations are supported including transactional SET.

Module invocation requires passing database type (sqlite3, psycopg,
MySQL and any other compliant to Python DB-API and importable as a Python
module) and connect string which is database dependant:

$ snmpsimd.py --variation-module-options=sql:sqlite3:/tmp/sqlite.db

The .snmprec value is expected to hold database table name to keep
all OID-value pairs served within selected .snmprec line. This table
will not be created automatically and should exist for sql module
to work. Table layout should be as follows:

  CREATE TABLE <tablename> (oid text primary key,
                            tag text,
                            value text,
                            maxaccess text default "read-only")

The most usual setup is to keep many OID-value pairs in a database
table referred to by a .snmprec line serving a subtree of OIDs:

  1.3.6.1.2.1.1|:sql|system

In the above case all OIDs under 1.3.6.1.2.1.1 prefix will be
handled by a sql module using 'system' table.

Custom variation modules
++++++++++++++++++++++++

Whenever you consider coding your own variation module, take a look at the
existing ones. The API is very simple - it basically takes three Python 
functions (init, process, shutdown) where process() is expected to return
a var-bind pair per each invocation.

Alternatively, we could help you with this task. Just let us know your
requirements.

Performance improvement
-----------------------

The SNMPv3 architecture is inherently computationally heavy so Simulator
is somewhat slow. It can run faster if it would use a much lighter and
lower-level SNMPv2c architecture at the expense of not supporting v3
operations.

Use the --v2c-arch command line parameter to switch Simulator into SNMPv2c
(v1/v2c) operation mode.

When Simulator runs over thousands of data files, startup may take time
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
Written by Ilya Etingof <ilya@glas.net>, 2010-2013
