#!/usr/bin/env bash

set -e

python scripts/snmprec.py --agent-udpv4-endpoint=demo.snmplabs.com
python scripts/mib2dev.py --mib-module=IF-MIB
