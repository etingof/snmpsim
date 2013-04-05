
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
  is appended. Reference to a variation module can also be embedded into tag.
* Value is either a printable string, a number or a hexifed value.

No other information or comments is allowed in the data file.

Device file recording would look like this:

$ snmprec.py  -h
SNMP Simulator version 0.2.1, written by Ilya Etingof <ilya@glas.net>
Software documentation and support at http://snmpsim.sf.net
Usage: scripts/snmprec.py [--help] [--debug=<category>] [--quiet] [--version=<1|2c|3>] [--community=<string>] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-priv-key=<key>] [--v3-auth-proto=<SHA|MD5>] [--v3-priv-proto=<3DES|AES256|DES|AES|AES128|AES192>] [--context=<string>] [--use-getbulk] [--getbulk-repetitions=<number>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--start-oid=<OID>] [--stop-oid=<OID>] [--output-file=<filename>] [--variation-modules-dir=<dir>] [--variation-module=<module>] [--variation-module-options=<args]>]
$
$ snmprec.py --agent-udpv4-endpoint=192.168.1.1 --start-oid=1.3.6.1.2.1 --stop-oid=1.3.6.1.2.1.5 --output-file=snmpsim/data/recorded/linksys-system.snmprec
Scanning "variation" directory for variation modules...  none requested
SNMP version 2c
Community name: public
Querying UDP/IPv4 agent at 192.168.1.1:161
Sending initial GETNEXT request....
OIDs dumped: 304, elapsed: 1.94 sec, rate: 157.00 OIDs/sec
$
$ ls -l data/recorded/linksys-system.snmprec 
-rw-r--r-- 1 ilya users 16252 Oct 26 14:49 data/recorded/linksys-system.snmprec 
$
$ head data/recorded/linksys-system.snmprec 
1.3.6.1.2.1.1.1.0|4|BEFSX41
1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.3955.1.1
1.3.6.1.2.1.1.3.0|67|638239
1.3.6.1.2.1.1.4.0|4|Linksys
1.3.6.1.2.1.1.5.0|4|isp-gw
1.3.6.1.2.1.1.6.0|4|4, Petersburger strasse, Berlin, Germany
1.3.6.1.2.1.1.8.0|67|4

There are no special requirements for data file name and location. Note,
that Simulator treats data file path as an SNMPv1/v2c community string
and its MD5 hash constitutes SNMPv3 context name.

About three times faster snapshot recording may be achieved by using SNMP's
GETBULK operation:

$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 --use-getbulk --output-file=data/recorded/linksys-system.snmprec

Faster recording may be important for capturing changes to Managed Objects
at better resolution.

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
SNMP Simulator version 0.2.1, written by Ilya Etingof <ilya@glas.net>
Software documentation and support at http://snmpsim.sf.net
Usage: scripts/mib2dev.py [--help] [--debug=<category>] [--quiet] [--pysnmp-mib-dir=<path>] [--mib-module=<name>] [--start-oid=<OID>] [--stop-oid=<OID>] [--manual-values] [--output-file=<filename>] [--string-pool=<words>] [--integer32-range=<min,max>]

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
snmpsim/data
snmpsim/data/public.snmprec
snmpsim/data/mib2dev
snmpsim/data/mib2dev/ip-mib.snmprec
snmpsim/data/mib2dev/host-resources-mib.snmprec
snmpsim/data/mib2dev/tcp-mib.snmprec
snmpsim/data/foreignformats
snmpsim/data/foreignformats/linux.snmpwalk
snmpsim/data/foreignformats/winxp.sapwalk
snmpsim/data/variation
snmpsim/data/variation/subprocess.snmprec
snmpsim/data/variation/virtualtable.snmprec
snmpsim/data/recorded
snmpsim/data/recorded/linksys-system.snmprec
snmpsim/data/recorded/udp-endpoint-table-walk.snmprec
...

There're also a bunch of .dbm files created and maintained automatically
in a temporary directory. These .dbm files are used by the Simulator
for fast OID lookup in a data file.

Getting help:

$ snmpsimd.py -h
SNMP Simulator version 0.2.1, written by Ilya Etingof <ilya@glas.net>
Software documentation and support at http://snmpsim.sf.net
Usage: scripts/snmpsimd.py [--help] [--version ] [--debug=<category>] [--data-dir=<dir>] [--cache-dir=<dir>] [--force-index-rebuild] [--validate-data] [--variation-modules-dir=<dir>] [--variation-module-options=<module[=alias][:args]>] [--agent-udpv4-endpoint=<X.X.X.X:NNNNN>] [--agent-udpv6-endpoint=<[X:X:..X]:NNNNN>] [--agent-unix-endpoint=</path/to/named/pipe>] [--v2c-arch] [--v3-only] [--v3-user=<username>] [--v3-auth-key=<key>] [--v3-auth-proto=<SHA|NONE|MD5>] [--v3-priv-key=<key>] [--v3-priv-proto=<3DES|AES256|NONE|DES|AES|AES128|AES192>]

Running Simulator:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161 --agent-udpv6-endpoint='[::1]:1161'
Scanning "/home/ilya/.snmpsim/variation" directory for variation modules...  no directory
Scanning "/usr/local/share/snmpsim/variation" directory for variation modules...  8 more modules found
Initializing variation modules:
    notification...  OK
    sql...  FAILED: database type not specified
    numeric...  OK
    subprocess...  OK
    delay...  OK
    multiplex...  OK
    error...  OK
    writecache...  OK
Scanning "/home/ilya/.snmpsim/data" directory for  *.snmpwalk, *.MVC, *.sapwalk, *.snmprec, *.dump data files... no directory
Scanning "/usr/local/share/snmpsim/data" directory for  *.snmpwalk, *.MVC, *.sapwalk, *.snmprec, *.dump data files...
==================================================================
Index /tmp/snmpsim/usr_local_share_snmpsim_data_public.dbm does not exist for data file data/public.snmprec
Building index /tmp/snmpsim/usr_local_share_snmpsim_data_public.dbm for data file /usr/local/share/snmpsim/data/public.snmprec (open flags "n")......133 entries indexed
Data file /usr/local/share/snmpsim/data/public.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: public
SNMPv3 context name: 4c9184f37cff01bcdc32dc486ec36961
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Index /tmp/snmpsim/usr_local_share_snmpsim_data_recorded_linksys-system.dbm does not exist for data file /usr/local/share/snmpsim/data/recorded/linksys-system.snmprec
Building index /tmp/snmpsim/usr_local_share_snmpsim_data_recorded_linksys-system.dbm for data file /usr/local/share/snmpsim/data/recorded/linksys-system.snmprec (open flags "n")......6 entries indexed
Data file /usr/local/share/snmpsim/data/recorded/linksys-system.snmprec, dbhash-indexed, closed
SNMPv1/2c community name: recorded/linksys-system
SNMPv3 context name: 1a764f7fd0e7b0bf98bada8fe723e488
-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
...
...
...
SNMPv3 credentials:
Username: simulator
Authentication key: auctoritas
Authentication protocol: MD5
Encryption (privacy) key: privatus
Encryption protocol: DES
Listening at:
  UDP/IPv4 endpoint 127.0.0.1:1161, transport ID 1.3.6.1.6.1.1.0
  UDP/IPv6 endpoint ::1:1161, transport ID 1.3.6.1.2.1.100.1.2.0


Simulator can listen at multiple local IP interfaces and/or UDP ports. Just
pass multiple --agent-udpv4-endpoint / --agent-udpv6-endpoint command
line parameters carrying addresses to listen on.

An unprivileged port is chosen in this example to avoid running as root.

At this point you can run you favorite SNMP Manager to talk to either
of the two simulated devices through whatever transport you prefer.
For instance, to talk to simulated Linux box over SNMP v2 through
UDP over IPv4 run:

$ snmpwalk -On -v2c -c recorded/linksys-system localhost:1161 1.3.6
.1.3.6.1.2.1.1.1.0 = STRING: BEFSX41
.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.3955.1.1
.1.3.6.1.2.1.1.3.0 = Timeticks: (638239) 1:46:22.39
.1.3.6.1.2.1.1.4.0 = STRING: Linksys
.1.3.6.1.2.1.1.5.0 = STRING: isp-gw
.1.3.6.1.2.1.1.6.0 = STRING: 4, Petersburger strasse, Berlin, Germany
.1.3.6.1.2.1.1.8.0 = Timeticks: (4) 0:00:00.04
.1.3.6.1.2.1.1.8.0 = No more variables left in this MIB View

To walk simulated 3com switch over SNMPv3 we'd run:

$ snmpwalk -On -n 1a764f7fd0e7b0bf98bada8fe723e488 -u simulator -A auctoritas -X privatus -lauthPriv localhost:1161 .1.3.6
.1.3.6.1.2.1.1.1.0 = STRING: BEFSX41
.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.3955.1.1
.1.3.6.1.2.1.1.3.0 = Timeticks: (638239) 1:46:22.39
.1.3.6.1.2.1.1.4.0 = STRING: Linksys
.1.3.6.1.2.1.1.5.0 = STRING: isp-gw
.1.3.6.1.2.1.1.6.0 = STRING: 4, Petersburger strasse, Berlin, Germany
.1.3.6.1.2.1.1.8.0 = Timeticks: (4) 0:00:00.04
.1.3.6.1.2.1.1.8.0 = No more variables left in this MIB View

Notice "-n <snmp-context>" parameter passed to snmpwalk to address particular
simulated device at Simulator.

Listing simulated devices
-------------------------

When simulating a large pool of devices or if your Simulator runs on a
distant machine, it is convenient to have a directory of all simulated
devices and their community/context names. Simulator maintains this
information within its internal, dedicated SNMP context 'index':

$ snmpwalk -On -v2c -c index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "data/public.snmprec"
.1.3.6.1.4.1.20408.999.1.1.2 = STRING: "data/mib2dev/ip-mib.snmprec"
...
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "public"
.1.3.6.1.4.1.20408.999.1.2.2 = STRING: "mib2dev/ip-mib"
...
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "4c9184f37cff01bcdc32dc486ec36961"
.1.3.6.1.4.1.20408.999.1.3.2 = STRING: "b545e61d091faca8a69f426b2bc5285d"
...

or

$ snmpwalk -On -l authPriv -u simulator -A auctoritas -X privatus -n index localhost:1161 .1.3.6
.1.3.6.1.4.1.20408.999.1.1.1 = STRING: "data/public.snmprec"
.1.3.6.1.4.1.20408.999.1.1.2 = STRING: "data/mib2dev/ip-mib.snmprec"
...
.1.3.6.1.4.1.20408.999.1.2.1 = STRING: "public"
.1.3.6.1.4.1.20408.999.1.2.2 = STRING: "mib2dev/ip-mib"
...
.1.3.6.1.4.1.20408.999.1.3.1 = STRING: "4c9184f37cff01bcdc32dc486ec36961"
.1.3.6.1.4.1.20408.999.1.3.2 = STRING: "b545e61d091faca8a69f426b2bc5285d"
...

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
read from the snapshot file being pointed toi:

$ ls -l public.snmprec 
-rw-r--r-- 1 ilya users 8036 Mar 12 23:26 public.snmprec
$ ln -s public.snmprec private.snmprec
$ ls -l private.snmprec 
lrwxrwxrwx 1 ilya users 14 Apr  5 20:58 private.snmprec -> public.snmprec
$

Shared data files are mentioned explicitly on Simulator startup:

$ snmpsimd.py --agent-udpv4-endpoint=127.0.0.1:1161
Scanning "/home/ilya/.snmpsim/variation" directory for variation modules...  no directory
Scanning "/usr/local/share/snmpsim/variation" directory for variation modules... 8 more modules found
Initializing variation modules:
    notification...  OK
    sql...  FAILED: database type not specified
    numeric...  OK
    subprocess...  OK
    delay...  OK
    multiplex...  OK
    error...  OK
    writecache...  OK
Scanning "/usr/local/share/snmpsim/data" directory for  *.snmpwalk, *.MVC, *.sapwalk, *.snmprec, *.dump data files...
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
^C

Now Managers can then use different credentials to access and modify the
same set of Managed Objects.

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

So snmpwalk outputs are exactly the same with different community names
used.

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

Simulation with variation modules
---------------------------------

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

* numeric - produces a non-decreasing sequence of integers over time
* notification - sends SNMP TRAP/INFORM messages to distant SNMP entity
* writecache - accepts and stores (in memory/file) SNMP var-binds modified
               through SNMP SET 
* sql - reads/writes var-binds from/to a SQL database
* delay - delays SNMP response by specified or random time
* error - flag errors in SNMP response PDU
* multiplex - use a collection of .snmprec files picking one at a time.
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
"writecache" module:

1.3.6.1.2.1.1.3.0|2:writecache|value=42

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

$ snmpsimd.py --variation-module-options=sql:dbtype:sqlite3,dboptions:/var/tmp/system.db

In case you are using multiple database connections or database types
all through the sql variation module, you could refer to each module instance
in .snmprec files through a so-called variation module alias.

The following command-line runs Simulator with two instances of the
"writecache" variation module (dbA & dbB) each instance using 
distinct database file for storing their persistent values:

$ snmpsimd.py --variation-module-options=writecache=dbA:file:/var/tmp/fileA.db --variation-module-options=writecache=dbB:file:/var/tmp/fileB.db

What follows is a brief description of some of the variation modules
included into the distribution.

Numeric module
++++++++++++++

The numeric module maintains and returns a changing in time integer value.
The law and rate of changing is configurable. This module is per-OID
stateful and configurable.

The numeric module accepts the following comma-separated key=value parameters
in .snmprec value field:

  min - the minimum value ever stored and returned by this module.
        Default is 0.
  max - the maximum value ever stored and returned by this module.
        Default is 2**32 or 2**64 (Counter64 type).
  initial - initial value. Default is min.
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
  increasing - if non-zero, assures the produced value is never decreasing
               (with possible exception of value wrapping on overflow).
               This is important when simulating COUNTER values.

This module generates values by execution of the following formula:

  v = function(UPTIME * rate) * scale + offset + RAND(increasing ? 0 : -deviation, deviation)

  v = increasing ? abs(v) : v

Here's an example numeric module use for various types in a .snmprec file:

  # COUNTER object
  1.3.6.1.2.1.2.2.1.13.1|65:numeric|initial=45,max=90,scale=0.6,deviation=1,function=cos,increasing=1,wrap=1

  # GAUGE object
  1.3.6.1.2.1.2.2.1.14.1|66:numeric|min=5,max=50,initial=25

The numeric module can be used for simulating INTEGER, Counter32, Counter64,
Gauge32, TimeTicks objects.

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
         Default is 500ms. If the value exceeds 999999, request will never
         be answered (PDU will be dropped right away).
  deviation - random delay deviation ranges (ms). Default is 0 which means no
              deviation.
  vlist - a list of triples (comparation:constant:delay) to use on SET 
          operation for choosing delay based on value supplied in request.
          The following comparations are supported: 'eq', 'lt', 'gt'.
  tlist - a list of triples (comparation:time:delay) to use for choosing
          request delay based on time of day (seconds, UNIX time).
          The following comparations are supported: 'eq', 'lt', 'gt'.

Here's an example delay module use in a .snmprec file.

The following entry makes Simulator responding with an integer value of 
6 delayed by 0.1sec +- 0.2 sec (negative delays are casted into zeros):

1.3.6.1.2.1.2.2.1.3.1|2:delay|value=6,wait=100,deviation=200

Here the hexvalue takes shape of an OCTET STRING value '0:12:79:62:f9:40'
delayed by exactly 0.8 sec:

1.3.6.1.2.1.2.2.1.6.1|4:delay|hexvalue=00127962f940,wait=800

This entry drops PDU right away so the Manager will timed out:

1.3.6.1.2.1.2.2.1.7.1|2:delay|wait=1000000

This entry uses module default on GET/GETNEXT/GETBULK operations, however
delays response on 0.1 sec if request value is exactly 0 and delays
response for 1 sec on value equal to 1.

1.3.6.1.2.1.2.2.1.8.1|2:delay|vlist=eq:0:100:eq:1:1000,value=1

The following entry uses module default on GET/GETNEXT/GETBULK operations,
however delays response on 0.001 sec if request value is exactly 100,
uses module default on values >= 100 but <= 300 (0.5 sec), and drops request
on values > 300:

1.3.6.1.2.1.2.2.1.9.1|67:delay|vlist=lt:100:1:gt:300:1000000,value=150

The next example will simulate an unavailable Agent past 01.04.2013

1.3.6.1.2.1.2.2.1.10.1|67:delay|tlist=gt:1364860800:1000000,value=150

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
  vlist - a list of triples (comparation:constant:error) to use as an access 
          list for SET values. The following comparations are supported:
          'eq', 'lt', 'gt'. The following SNMP errors are supported:
          'generror', 'noaccess', 'wrongtype', 'wrongvalue', 'nocreation',
          'inconsistentvalue', 'resourceunavailable', 'commitfailed',
          'undofailed', 'authorizationerror', 'notwritable', 
          'inconsistentname', 'nosuchobject', 'nosuchinstance', 'endofmib'

Here's an example error module use in a .snmprec file:

1.3.6.1.2.1.2.2.1.1.1|2:error|op=get,status=authorizationError,value=1
1.3.6.1.2.1.2.2.1.2.1|4:error|op=set,status=commitfailed,hexvalue=00127962f940
1.3.6.1.2.1.2.2.1.3.1|2:error|vlist=gt:2:wrongvalue,value=1
1.3.6.1.2.1.2.2.1.6.1|4:error|status=noaccess

The first entry flags 'authorizationError' on GET* and no error
on SET. Second entry flags 'commitfailed' on SET but responds without errors
to GET*. Third entry fails with 'wrongvalue' only on SET with values > 2.
Finally, forth entry always flags 'noaccess' error.

Write Cache module
++++++++++++++++++

The writecache module lets you make particular OID at a .snmprec file
writable via SNMP SET operation. The new value will be stored in Simulator
process's memory or disk-based datastore and communicated back on SNMP 
GET/GETNEXT/GETBULK operations.
Data saved in disk-based datastore will NOT be lost upon Simulator restart.

Module initialization allows for passing a name of a database file to be
used as a disk-based datastore:

$ snmpsimd.py --variation-module-options=writecache:file:/tmp/shelves.db

All modifed values will be kept and then subsequently used on a per-OID
basis in the specified file. If datastore file is not specified, the
writecache.py module will keep all its data in [volatile] memory.

The writecache module accepts the following comma-separated key=value
parameters in .snmprec value field:

  value - holds the var-bind value to be included into SNMP response.
          In case of a string value containing commas, use 'hexvalue'
          instead.
  hexvalue - holds the var-bind value as a sequence of ASCII codes in hex
             form. Before putting it into var-bind, hexvalue contents will
             be converted into ASCII text.
  vlist - a list of triples (comparation:constant:error) to use as an access 
          list for SET values. The following comparations are supported:
          'eq', 'lt', 'gt'. The following SNMP errors are supported:
          'generror', 'noaccess', 'wrongtype', 'wrongvalue', 'nocreation',
          'inconsistentvalue', 'resourceunavailable', 'commitfailed',
          'undofailed', 'authorizationerror', 'notwritable', 
          'inconsistentname', 'nosuchobject', 'nosuchinstance', 'endofmib'

Here's an example writecache module use in a .snmprec file:

1.3.6.1.2.1.1.3.0|2:writecache|value=42

In the above configuration, the initial value is 42 and can be modified by:

snmpset -v2c -c <commiunity> localhost 1.3.6.1.2.1.1.3.0 i 24

command (assuming correct community name and Simulator is running locally).

A more complex example involves using an access list. The following example
allows only values of 1 and 2 to be SET:

1.3.6.1.2.1.1.3.0|2:writecache|value=42,vlist=lt:1:wrongvalue:gt:2:wrongvalue

Any other SET values will result in SNNP WrongValue error in response.

Multiplex module
++++++++++++++++

The multiplex module allows you to serve many snapshots for a single Agent
picking just one snapshot at a time for answering SNMP request. That
simulates a more natural Agent behaviour including the set of OIDs changing
in time.

This module is usually configured to serve an OID subtree in an .snmprec
file entry.

The multiplex module accepts the following comma-separated key=value 
parameters in .snmprec value field:

  dir - path to .snmprec files directory. If path is not absolute, it
        is interpreted relative to Simulator's "data" directory. The
        .snmprec files names here must have numerical names ordered
        by time.
  period - specifies for how long to use each .snmprec snapshot before
           switching to the next one. Default is 60 seconds.
  wrap - if true, instructs the module to cycle through all available
         .snmprec files. If faulse, the system stops switching .snmprec
         files as it reaches the last one. Default is false.

Here's an example of multiplex module use:
 
1.3.6.1.2.1.2|:multiplex|dir=variation/snapshots,period=10.0
1.3.6.1.3.1.1|4|system

The .snmprec files served by the multiplex module can not include references
to variation modules.

Subprocess module
+++++++++++++++++

The subprocess module can be used to execute an external program
passing it request data and using its stdout output as a response value.

Module invocation supports passing a 'shell' option which (if true) makes
Simulator using shell for subprocess invocation. Default is True on
Windows platform and False on all others.

$ snmpsimd.py --variation-module-options=subprocess:shell:1

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
  vlist - a list of duplets (comparation:constant) to use as event
          triggering criteria to be compared against SET values. The
          following comparations are supported: 'eq', 'lt', 'gt'.
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
module) and connect string which is database dependant. For example,
sqlite backend can be configured this way:

$ snmpsimd.py --variation-module-options=sql:sqlite3:/tmp/sqlite.db

The .snmprec value is expected to hold database table name to keep
all OID-value pairs served within selected .snmprec line. This table
can either be created automatically whenever sql module is invoked in
recording mode or can be created and populated by hand. In the latter case
table layout should be as follows:

  CREATE TABLE <tablename> (oid text primary key,
                            tag text,
                            value text,
                            maxaccess text default "read-only")

The most usual setup is to keep many OID-value pairs in a database
table referred to by a .snmprec line serving a subtree of OIDs:

  1.3.6.1.2.1.1|:sql|system

In the above case all OIDs under 1.3.6.1.2.1.1 prefix will be
handled by a sql module using 'system' table.

Please, note, that to make SQL's ORDER BY clause working with OIDs,
each sub-OID stored in the database (in case of manual database population) 
must be left-padded with a good bunch of spaces (each sub-OID width
is 10 characters).

Recording with variation modules
--------------------------------

Some valuable simulation information may also be collected in the process 
of recording snapshots off live SNMP Agent. Examples include changes in the
set of OIDs in time, changes in numeric values, request processing times
and so on. To facilitate capturing such information, some of the stock
variation modules support snapshots recording mode.

To invoke a variation module while snapshotting a SNMP Agent with 
snmprec.py tool, pass its name via the --variation-module command-line 
parameter. Additional variation module parameters could also be passed
through the --variation-module-options switch.

In the following sections we will outline the use of recording facilities
in stock variation modules:

Numeric module
++++++++++++++

The numeric module can be used for capturing initial values of
Managed Objects and calculating a coefficient to a linear function
in attempt to approximate live values changes in time. In case value
change law is not linear, custom approximation function should be used
instead.

The numeric module supports the following comma-separated key:value
options whilst running in recording mode:

  taglist - a dash-separated list of .snmprec tags indicating SNMP
            value types to apply numeric module to. Valid tags are:
            Integer - 2, 65 - Counter32, 66 - Gauge32, 67 - TimeTicks,
            70 - Counter64. Default is empty list.
  iterations - number of times snmprec.py will walk the specified 
               [portion] of Agent's MIB tree. There's no point in values
               beyond 2 for purposes of modelling approximation function.
               Default is 1.
  period - Agent walk period in seconds. Default is 10 seconds.
  addon - a single snmprec record scope key=value parameter for the
          multiplex module to be used whilst running in variation mode.
          Multiple addon parameters can be used. Default is empty.

Example use of numeric module for recording follows:

$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 
  --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 
  --variation-module=numeric 
  --variation-module-options=taglist:65,iterations:2,period:15
Scanning "variation" directory for variation modules...numeric module loaded
SNMP version 2c
Community name: public
Querying UDP/IPv4 agent at 127.0.0.1:161
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
itself into generated .snmprec data for Counter32-typed objects (ID 65).

Produced snmprec could be used for simulation as-is or edited by
hand to change variation module behaviour on on a per-OID basis..

Delay module
++++++++++++

The delay module can be used for capturing request processing time
when snapshotting an Agent.

Example use of delay module for recording follows:

$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 
  --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 
  --variation-module=delay
Scanning "variation" directory for variation modules...delay module loaded
SNMP version 2c
Community name: public
Querying UDP/IPv4 agent at 127.0.0.1:161
Initializing variation module:
    delay...OK
1.3.6.1.2.1.2.1.0|2:delay|value=5,wait=8
1.3.6.1.2.1.2.2.1.1.1|2:delay|value=1,wait=32
1.3.6.1.2.1.2.2.1.6.4|4x:delay|hexvalue=008d120f4fa4,wait=20
...
Shutting down variation modules:
    delay...OK
OIDs dumped: 224, elapsed: 15.53 sec, rate: 20.00 OIDs/sec

Produced snmprec could be used for Simulation as-is or edited by
hand to change delay variation.

Multiplex module
++++++++++++++++

The multiplex module can record a series of snapshots at specified period
of time. Recorded .snmprec snapshots could then be used for simulation
by multiplex module.

The multiplex module supports the following comma-separated key:value
options whilst running in recording mode:

  dir - directory for produced .snmprec files.
  iterations - number of times snmprec.py will walk the specified 
               [portion] of Agent's MIB tree.  Default is 1.
  period - Agent walk period in seconds. Default is 10 seconds.
  addon - a single snmprec record scope key=value parameter for the
          multiplex module to be used whilst running in variation mode.
          Multiple addon parameters can be used. Default is empty.

Example use of numeric module for recording follows:

$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 
  --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 
  --output-file=data/multiplex.snmprec
  --variation-module=multiplex
  --variation-module-options=dir:data/multiplex:,iterations:5,period:15
Scanning "variation" directory for variation modules...multiplex module loaded
SNMP version 2c
Community name: public
Querying UDP/IPv4 agent at 127.0.0.1:161
Initializing variation module:
    multiplex...OK
multiplex: writing into data/multiplex/00000.snmprec file...
multiplex: waiting 14.78 sec(s), 45 OIDs dumped, 5 iterations remaining...
...
multiplex: writing into data/multiplex/00005.snmprec file...            
Shutting down variation modules:
    multiplex...OK
OIDs dumped: 276, elapsed: 75.76 sec, rate: 3.64 OIDs/sec

Besides individual snmprec snapshots the "main" .snmprec file will also
be written:

$ cat data/multiplex.snmprec
1.3.6.1.2.1.2|:multiplex|period=15.00,dir=data/multiplex
$

where the multiplex module is configured for specific OID subtree (actually,
specified in --start-oid).

Although multiplex-generated .snmprec files can also be addressed directly
by Simulator, it's more conventional to access them through "main" .snmprec
file and multiplex module.

SQL module
++++++++++

The sql module can record a snapshot of Agent's set of Managed Objects
and store it in a SQL database. Recorded snapshots could then be used
for simulation by sql module running in varition mode.

The sql module supports the following comma-separated key:value
options whilst running in recording mode:

  dbtype - SQL DBMS type in form of Python DPI API-compliant module.
           It will be imported into Python as specified.
  dboptions - DBMS module connect string in form of arg1@arg2@arg3...
  dbtable - SQL table name to use for storing recorded snapshot.

Here's an example use of sql module with Python built-in SQLite
database for snapshot recording purposes:

$ snmprec.py --agent-udpv4-endpoint=127.0.0.1 
  --start-oid=1.3.6.1.2.1.2 --stop-oid=1.3.6.1.2.1.3 
  --output-file=data/sql.snmprec
  --variation-module=sql
  --variation-module-options=dbtype:sqlite3,dboptions:/tmp/snmpsim.db,dbtable:snmprec
Scanning "variation" directory for variation modules... sql module loaded
SNMP version 2c
Community name: public
Querying UDP/IPv4 agent at 127.0.0.1:161
Initializing variation module:
    sql...OK
Shutting down variation modules:
    sql...OK
OIDs dumped: 45, elapsed: 0.21 sec, rate: 213.00 OIDs/sec

By this point you'd get the data/sql.snmprec file where sql module
is configured for OID subtree (taked from --start-oid parameter):

$ cat data/sql.snmprec
1.3.6.1.2.1.2.2|:sql|snmprec
$

and SQLite database /tmp/snmpsim.db having SQL table "snmprec" with the
following contents:

$ sqlite3 /tmp/snmpsim.db 
SQLite version 3.7.5
sqlite> .schema snmprec
CREATE TABLE snmprec (oid text primary key, tag text, value text, maxaccess text default "read-only");
sqlite> select * from snmprec limit 1;
         1.         3.         6.         1.         2.         1.         2.         2.         1.         1.         1|2|1|read-write

Notice the format of the OIDs there -- each sub-oid is left-padded with
up to 8 spaces (must be 10 chars in total) to make OIDs ordering work 
properly with SQL sorting facilities.

When sql variation module is invoked by Simulator, it can read, create and
modify individual rows in the SQL database we just created (this is
described in relevant section of this document).

You could also modify the contents of such SQL tables, create SQL triggers
to react to certain changes elsewhere.

Custom variation modules
++++++++++++++++++++++++

Whenever you consider coding your own variation module, take a look at the
existing ones. The API is not too complex - it basically takes four Python 
functions (init, variate, record and shutdown) where variate() accepts
the oid-tag-value triplet from matching snmprec record as well as execution
context. Its return value is expected to be an oid-tag-value triplet to be
used for building response.

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

To use Simulator on a Windows machine, simply download and run supplied
executable to install pre-compiled binaries and demo data files.

https://sourceforge.net/projects/snmpsim

On other platforms, installation from source code is advised. The
installation procedure for SNMP Simulator is as follows:

$ tar zxf snmpsim-X.X.X.tar.gz
$ cd snmpsim-X.X.X
# python setup.py install
# cd ..
# rm -rf package-X.X.X

Required packages will be automatically downloaded and installed.

In case you are installing Simulator on an off-line system, the following
packages need to be downloaded and installed for Simulator to become
operational:

* PyASN1, used for handling SNMP/ASN.1 objects:

  http://sourceforge.net/projects/pyasn1/

* PySNMP, SNMP engine implementation:

  http://sourceforge.net/projects/pysnmp/

* The SNMP Simulator package

Optional, but recommended:

* PyCrypto, used by SNMPv3 crypto features (Windows users installing from
  source need precompiled version):

  http://www.pycrypto.org

MIBs collection as PySNMP modules, if you are planning a MIB-based simulation

The installation procedure for all the above packages is as follows (on 
UNIX-based systems):

$ tar zxf package-X.X.X.tar.gz
$ cd package-X.X.X
# python setup.py install
# cd ..
# rm -rf package-X.X.X

Demo data files and stock variation modules will be installed in a
platform-dependent location. Watch installation log for exact location.
You could also put your own SNMP snapshots into your home directory for
Simulator to find them there. Watch Simulator output for hints.

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
