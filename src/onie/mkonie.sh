#!/bin/sh
#
######################################################################
#
# mkonie.sh
#
# Generate the ONIE kvm profile
#
######################################################################

set -e

CMD=${0##*/}

SNAP=$PWD/vda-snap.qcow
MAC=52:54:00:9B:57:A7
VM=roth-onie
UUID=$(uuidgen)

echo "$CMD: generating ONIE XML"
sed \
  -e "s|@MAC@|${MAC}|" \
  -e "s|@VM@|${VM}|" \
  -e "s|@UUID@|${UUID}|" \
  -e "s|@VDA@|${SNAP}|" \
  onie-qemu.xml.in > onie-qemu.xml

echo "$CMD: defining VM"
virsh destroy $VM || :
virsh undefine $VM || :
virsh define onie-qemu.xml

exit 0

