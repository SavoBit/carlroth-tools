#!/bin/sh

#  Copyright (C) 2014 Curt Brune <curt@cumulusnetworks.com>
#
#  SPDX-License-Identifier:     GPL-2.0

bindir=$(dirname $0)
bindir=$(cd $bindir && pwd)

MEM=1024
DISK="$PWD/onie-x86-demo.qcow"
SNAP="$PWD/vda-snap.qcow"
IMG="$PWD/vda.img"

# Path to OVMF firmware for qemu
# Download OVMF from http://www.tianocore.org/ovmf/
OVMF="$HOME/kvm/OVMF.fd"

# VM will listen on telnet port $KVM_PORT
KVM_PORT=9000

# VNC display to use
VNC_PORT=0

MAC=52:54:00:9B:57:A7

IFUP=$bindir/qemu-ifup

# set mode=disk to boot from hard disk
mode=disk

# set mode=cdrom to boot from the CDROM
# mode=cdrom

# set mode=net to boot from network adapters
# mode=net

# set firmware=uefi to boot with UEFI firmware, otherwise the system
# will boot into legacy mode.
##firmware=uefi

on_exit()
{
    rm -f $kvm_log
}

kvm_log=$(mktemp)
trap on_exit EXIT

boot=c
if [ "$mode" = "cdrom" ] ; then
    boot="order=cd,once=d"
    cdrom="-cdrom $CDROM"
elif [ "$mode" = "net" ] ; then
    boot="order=cd,once=n,menu=on"
fi

if [ "$firmware" = "uefi" ] ; then
    [ -r "$OVMF" ] || {
        echo "ERROR:  Cannot find the OVMF firmware for UEFI: $OVMF"
        echo "Please make sure to install the OVMF.fd in the expected directory"
        exit 1
    }
    bios="-bios $OVMF"
fi

if test "$NOIMG"; then
  echo "*** re-using existing disk images" 1>&2
else
  echo "generating disk images" 1>&2
  sudo rm -f $SNAP
  ##qemu-img create -o backing_file=$DISK -f qcow $SNAP
  qemu-img convert -O raw $DISK $IMG
fi

# See
# http://www.linux-kvm.com/content/how-maximize-virtio-net-performance-vhost-net
# for pci option syntax

if ip link show br0 1>/dev/null 2>&1; then
  :
else
  echo "Missing br0 interface!"
  exit 1
fi

sudo /usr/bin/kvm -m $MEM \
    -name "onie" \
    $bios \
    -boot $boot $cdrom \
    -netdev tap,id=roth0,script="$IFUP",downscript="no" \
    -device virtio-net-pci,netdev=roth0,mac=$MAC,bus=pci.0,addr=0x3 \
    -nographic -echr 1 \
    -serial mon:telnet:localhost:9000,server,wait \
    -drive file=$IMG,media=disk,if=virtio,index=0 > vm.out 2>&1 &
pid=$!

##    -net tap,ifname=roth0,script="$IFUP",downscript="no" \
##    -net nic,model=virtio,macaddr=$MAC \

sleep 1
reset
script -c "telnet localhost 9000" -a -f -q vm.out
reset

if ps -o pid= -p $pid 1>/dev/null 2>&1; then
    echo "Reconnect to monitor with: telnet localhost 9000"
    echo "Kill vm with: sudo kill $pid"
fi
echo "See logs in vm.out"

exit 0
