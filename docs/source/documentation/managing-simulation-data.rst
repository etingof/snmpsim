
.. _managing-simulation-data:

Simulation data
===============

SNMP agent simulation revolves around the contents of *.snmprec* files.

.. _snmprec:

File format
-----------

The *.snmprec* file format is optimised to be compact, human-readable and
inexpensive to parse. It's also important to store full and exact
response information in a most intact form. Here's an example data
file content:

.. code-block:: bash

    1.3.6.1.2.1.1.1.0|4|Linux 2.6.25.5-smp SMP Tue Jun 19 14:58:11 CDT 2007 i686
    1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.8072.3.2.10
    1.3.6.1.2.1.1.3.0|67|233425120
    1.3.6.1.2.1.2.2.1.6.2|4x|00127962f940
    1.3.6.1.2.1.4.22.1.3.2.192.21.54.7|64x|c3dafe61

There is a pipe-separated triplet of *OID|tag|value* items where:

* OID is a dot-separated set of numbers
* Tag is a BER-encoded ASN.1 tag. A modifier can be appended to the
  tag number. The following modifiers are known:

    - *x* when the value is hexified (e.g. '0102')
    - *e* when the value is a Python string literal (e.g. '\x01\x02hello')
    - Colon-separated reference to a variation module

* The value is either a printable string or a hexified string or a raw
  Python string. Unless it's a number.

Valid tag values and their corresponding ASN.1/SNMP types are:

* 2 - Integer32
* 4 - OCTET STRING
* 5 - NULL
* 6 - OBJECT IDENTIFIER
* 64 - IpAddress
* 65 - Counter32
* 66 - Gauge32
* 67 - TimeTicks
* 68 - Opaque
* 70 - Counter64

Besides plain-text form, compressed *.snmprec.bz2* files are also supported.

.. _snmpsim-manage-records:

Managing data files
-------------------

The *snmpsim-manage-records* tool is designed to perform a few handy operations
on the data files.

If you possess *.snmpwalk* or *.sapwalk* snapshots and wish to convert them
into Simulator's native *.snmprec* data file format (what can be required
for using variation modules), run the *snmpsim-manage-records* tool like this:

.. code-block:: bash

    $ snmpsim-manage-records --input-file=linux.snmpwalk \
        --source-record-type=snmpwalk
    1.3.6.1.2.1.1.1.0|4|Linux cray 2.6.37.6-smp #2 SMP Sat Apr 9 23:39:07 CDT 2011 i686
    1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.8072.3.2.10
    1.3.6.1.2.1.1.3.0|67|121722922
    1.3.6.1.2.1.1.4.0|4|Root <root@cray> (configure /etc/snmp/snmp.local.conf)
    1.3.6.1.2.1.1.5.0|4|new system name
    1.3.6.1.2.1.1.6.0|4|KK12 (edit /etc/snmp/snmpd.conf)
    1.3.6.1.2.1.1.8.0|67|0
    1.3.6.1.2.1.1.9.1.2.1|6|1.3.6.1.6.3.11.2.3.1.1
    1.3.6.1.2.1.1.9.1.2.2|6|1.3.6.1.6.3.15.2.1.1
    1.3.6.1.2.1.1.9.1.2.3|6|1.3.6.1.6.3.10.3.1.1
    ...
    # Records: written 3711, filtered out 0, deduplicated 0, broken 0, variated 0

SNMP Simulator requires data files to be sorted (by OID) and containing no
duplicate OIDs. In case your data file does not comply with these requirements
for some reason, you could pass it through the *snmpsim-manage-records* tool to
fix data file:

.. code-block:: bash

    $ snmpsim-manage-records --input-file=tcp-mib.snmprec --sort-records
      --ignore-broken-records --deduplicate-records
    1.3.6.1.2.1.6.1.0|2|1
    1.3.6.1.2.1.6.2.0|2|4
    1.3.6.1.2.1.6.3.0|2|2
    1.3.6.1.2.1.6.4.0|2|4
    ...
    1.3.6.1.2.1.6.20.1.2.2.0.432|4|
    1.3.6.1.2.1.6.20.1.3.2.0.432|66|80
    1.3.6.1.2.1.6.20.1.4.2.0.432|66|1524968792
    # Records: written 33, filtered out 0, deduplicated 0, broken 0, variated 0

If you have a huge data file and wish to use just a part of it for
simulation purposes, snmpsim-manage-records tool could cut a slice form a
data file and store records in a new one:

.. code-block:: bash

    $ snmpsim-manage-records --input-file=tcp-mib.snmprec \
        --start-oid=1.3.6.1.2.1.6.13 --stop-oid=1.3.6.1.2.1.6.14
    1.3.6.1.2.1.6.13.1.1.72.192.51.208.2.234.233.215.7.3|2|1
    1.3.6.1.2.1.6.13.1.2.72.192.51.208.2.234.233.215.7.3|64x|8b896863
    1.3.6.1.2.1.6.13.1.3.72.192.51.208.2.234.233.215.7.3|2|3
    1.3.6.1.2.1.6.13.1.4.72.192.51.208.2.234.233.215.7.3|64x|4f1182fe
    1.3.6.1.2.1.6.13.1.5.72.192.51.208.2.234.233.215.7.3|2|3
    # Records: written 5, filtered out 28, deduplicated 0, broken 0, variated 0

Merge of multiple data files into a single data file is also supported:

.. code-block:: bash

    $ snmpsim-manage-records --input-file=tcp-mib.snmprec \
        --input-file=udp-mib.snmprec --sort-records \
        --deduplicate-records
    1.3.6.1.2.1.6.1.0|2|1
    1.3.6.1.2.1.6.2.0|2|4
    1.3.6.1.2.1.6.3.0|2|2
    1.3.6.1.2.1.6.4.0|2|4
    ...
    1.3.6.1.2.1.7.8.0|70|3896031866066683889
    1.3.6.1.2.1.7.9.0|70|3518073560493506800
    # Records: written 49, filtered out 0, deduplicated 0, broken 0, variated 0

Having string values more human-readable may be more convenient in the
course of adjusting simulation data, debugging etc. By default, strings in
simulation data are hexified. By passing such *.snmprec* file through
the *snmpsim-manage-records --escaped-strings* call, you can convert your
*.snmprec* data into Python string literal representation:

.. code-block:: bash

    $ head data/sample.snmprec
    1.3.6.1.2.1.55.1.5.1.8.2|4x|00127962f940
    $
    $ snmpsim-manage-records --source-record-type=snmprec  \
        --input-file=data/sample.snmprec --escaped-strings
    1.3.6.1.2.1.55.1.5.1.8.2|4e|\x00\x12yb\xf9@
    # Records: written 1, filtered out 0, deduplicated 0, broken 0, variated 0
