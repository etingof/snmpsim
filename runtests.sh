#!/usr/bin/env bash

set -e

snmpsim-record-commands --agent-udpv4-endpoint=demo.snmplabs.com
# this fails with new pysnmp's TEXTUAL-CONVENTION parser
# snmpsim-record-mibs --mib-module=IF-MIB
snmpsim-record-mibs --mib-module=SNMPv2-MIB
