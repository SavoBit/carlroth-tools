#!/bin/sh
#
######################################################################
#
# mkembed.sh
#
# Generate the initial ONIE kvm disk image
#
######################################################################

set -e

CMD=${0##*/}

##TMPDIR=${TMPDIR-"/tmp"}
TMPDIR=/mnt/Users/roth/work/tmp
export TMPDIR

IMG=${TMPDIR}/onie.img
QCOW=onie-x86-demo.qcow
SNAP=vda-snap.qcow
MAC=52:54:00:a6:fb:50
VM=onie
# See http://switch-nfs.hw.bigswitch.com/export/ONIE/5cfd81b89a5774b99d7058025ff06c85d23cfaf8/kvm_x86_64-r0/
ISO=$PWD/onie-recovery-x86_64-kvm_x86_64-r0.iso
UUID=$(uuidgen)

# ugh, this is too big, but the SL loader assumes
# a disk of at least 32GiB
echo "$CMD: generating 48GiB blank disk image"
dd if=/dev/zero of=$IMG bs=1048576 count=49152

echo "$CMD: generating installer XML"
sed \
  -e "s|@MAC@|${MAC}|" \
  -e "s|@IMG@|${IMG}|" \
  -e "s|@ISO@|${ISO}|" \
  -e "s|@VM@|${VM}|" \
  -e "s|@UUID@|${UUID}|" \
  onie-embed-qemu.xml.in > onie-embed-qemu.xml

echo "$CMD: defining VM"
virsh destroy $VM || :
virsh undefine $VM || :
virsh define onie-embed-qemu.xml

echo "$CMD: drive the VM through the embed process, then exit"
read -p "Hit CR to continue... " foo

echo "$CMD: shutting down VM"
virsh destroy $VM || :
virsh undefine $VM

echo "$CMD: creating base QCOW"
rm -f $QCOW
qemu-img convert -c -f raw -O qcow $IMG $QCOW

echo "$CMD: creating snapshot"
/bin/rm -f $SNAP
qemu-img create -o backing_file=$QCOW -f qcow $SNAP

exit 0

