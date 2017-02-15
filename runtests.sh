#!/usr/bin/env bash

set -e

python scripts/snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com
# this fails with new pysnmp's TEXTUAL-CONVENTION parser
# python scripts/mib2dev.py --mib-module=IF-MIB
python scripts/mib2dev.py --mib-module=SNMPv2-MIB
