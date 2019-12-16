#!/bin/bash
#
# Stand up a couple of SNMP command responders, torture them
# with SNMP command recorders in many different ways.
#
# Fail the entire script on any failure.
#

set -e

snmpsim-command-responder \
    --log-level error \
    --data-dir data \
    --variation-modules-dir variation \
    --agent-udpv4-endpoint 127.0.0.1:1161 \
    --agent-udpv4-endpoint 127.0.0.1:1162 &

SNMPSIMD_1_PID=$!

snmpsim-command-responder-lite \
    --log-level error \
    --data-dir data \
    --variation-modules-dir variation \
    --agent-udpv4-endpoint 127.0.0.1:1163 &

SNMPSIMD_2_PID=$!

SNMPSIMD_LOG=$(mktemp /tmp/snmpsimd.XXXXXX)
SNMPREC_LOG=$(mktemp /tmp/snmprec.XXXXXX)
MIB2DEV_LOG=$(mktemp /tmp/mib2dev.XXXXXX)

function cleanup()
{
    rm -f $SNMPSIMD_LOG $SNMPSIMD_LOG $MIB2DEV_LOG
    kill $SNMPSIMD_1_PID $SNMPSIMD_2_PID
}

trap cleanup EXIT

# test snmpsimd instance, 1-st endpoint
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1161

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, 2-nd endpoint
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1162

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, timeout
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1165 || { echo This is the expected timeout; }

# test snmpsimd instance, numeric module
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --community variation/virtualtable \
    --agent-udpv4-endpoint=127.0.0.1:1162

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, snmpwalk format
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --community foreignformats/linux \
    --agent-udpv4-endpoint=127.0.0.1:1162

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, sapwalk format
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --community foreignformats/winxp2 \
    --agent-udpv4-endpoint=127.0.0.1:1162

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, GETBULK mode
snmpsim-record-commands \
    --log-level error \
    --use-getbulk \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1161

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, v3 noAuthNoPriv
snmpsim-record-commands \
    --log-level error \
    --v3-user simulator \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1161

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, v3 authNoPriv
snmpsim-record-commands \
    --log-level error \
    --v3-user simulator \
    --v3-auth-key auctoritas \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1161

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test snmpsimd instance, v3 authPriv
snmpsim-record-commands \
    --log-level error \
    --v3-user simulator \
    --v3-auth-key auctoritas \
    --v3-priv-key privatus \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1161

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# test lite snmpsim instance
snmpsim-record-commands \
    --log-level error \
    --output-file $SNMPREC_LOG \
    --agent-udpv4-endpoint=127.0.0.1:1163

[ -z $SNMPREC_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }

rm -f $SNMPREC_LOG

# TODO: Fails on --log-level and something else
#snmpsim-record-mibs \
#    --log-level error \
#    --output-file $MIB2DEV_LOG \
#    --mib-module=SNMPv2-MIB
#
#[ -z $MIB2DEV_LOG ] && { echo "Empty .snmprec generated"; exit 1 ; }
#
#rm -f $MIB2DEV_LOG

echo "It works! \o/"
