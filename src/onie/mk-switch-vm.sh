#!/bin/bash
#
######################################################################
#
# mk-switch-vm.sh
#
######################################################################

bindir=$(dirname $0)
bindir=$(cd $bindir && pwd)

NAME="switch-vm"

MEM=8192

DISK="$PWD/onie-x86-demo.qcow"
# Use this for ONL

##DISK="$PWD/z_bs3240_template.qcow2"
DISK="$PWD/z_bs3240_template_8g.qcow2"
# Use this for SWL and switchlight

SNAP="$PWD/${NAME}-vda-snap.qcow"
IMG="$PWD/${NAME}-vda.img"

# Path to OVMF firmware for qemu
# Download OVMF from http://www.tianocore.org/ovmf/
OVMF="/usr/share/ovmf/OVMF.fd"

# path to embed ISO
if test "$NOEMBED"; then
  :
else

  ##EMBED=${EMBED-"$PWD/onie-recovery-x86_64-kvm_x86_64-r0.iso"}
  ### Use this for ONL

  EMBED=${EMBED-"$PWD/onie-recovery-x86_64-bigswitch_bs3240-r0-2016.05.BSN.1-BS3240.iso"}
  # Use this for SWL and switchlight

fi

# VM will listen on telnet port $KVM_PORT
# For BCF-4.2, this needs to be an emulated serial port
KVM_PORT=9000

# VNC display to use
VNC_PORT=0

MAC=52:54:00:9B:57:A7

if id -nG | grep -q libvirt; then
  :
else
  echo "*** not in the libvirt group" 1>&2
  exit 1
fi

on_exit()
{
    rm -f $kvm_log
}

kvm_log=$(mktemp)
trap on_exit EXIT

if test -f "$OVMF"; then
  BIOS="$PWD/${NAME}-bios.img"
fi

if test "$NOIMG"; then
  echo "*** re-using existing disk images" 1>&2
else
  echo "generating disk images" 1>&2
  sudo rm -f $SNAP
  ##qemu-img create -o backing_file=$DISK -f qcow $SNAP

  sudo rm -f $IMG
  # once the VM is running it is owned by a root-ish user
  
  qemu-img convert -O raw $DISK $IMG || exit 1

  if test -f "$OVMF"; then
    cp $OVMF $BIOS || exit 1

    sudo chown libvirt-qemu $BIOS || exit 1
    # libvirt has funny startup requirements for perms on the BIOS;
    # for normal disk images is is fine to chown as it goes
  fi
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

virsh destroy "$NAME" || :
virsh undefine "$NAME" || :

OPTS=
OPTS=$OPTS${OPTS:+" "}"-r $MEM"
OPTS=$OPTS${OPTS:+" "}"-n $NAME"

##############################
#
# Try to emulate bs3240
#
##############################
OPTS=$OPTS${OPTS:+" "}"--machine pc-i440fx-2.1"
##OPTS=$OPTS${OPTS:+" "}"--cpu Opteron_G4"

if test -f "$EMBED"; then
  OPTS=$OPTS${OPTS:+" "}"--disk path=$EMBED,device=cdrom,format=raw"
else
  OPTS=$OPTS${OPTS:+" "}"--disk device=cdrom,format=raw"
fi
OPTS=$OPTS${OPTS:+" "}"--disk path=$IMG,device=disk,bus=virtio,format=raw"
OPTS=$OPTS${OPTS:+" "}"--import --noautoconsole"

# Ugh, buggy BIOS w.r.t. virtio-net
if test -f "$BIOS"; then
  echo "FOO!"
  OPTS=$OPTS${OPTS:+" "}"--network=bridge:br0,mac=$MAC,model=e1000"
else
  OPTS=$OPTS${OPTS:+" "}"--network=bridge:br0,mac=$MAC,model=virtio"
fi

OPTS=$OPTS${OPTS:+" "}"--graphics vnc,listen=0.0.0.0,password=bsn"

echo "Generating XML for $NAME"
virt-install --connect qemu:///system --print-xml $OPTS > ${NAME}.xml
sts=$?
test $sts -eq 0 || exit $sts

if test -f "$BIOS"; then
  echo "Adding bios declaration from $BIOS"
  BIOS_=${BIOS//\//\\\/}
  sed -i -e "/[<]os[>]/a\\<loader type='pflash'>${BIOS_}</loader>\\n" ${NAME}.xml
fi

# update the crash/reboot behavior for debugging
if true; then
  sed -i -e "/[<]on_reboot[>]/d" ${NAME}.xml
  sed -i -e "/[<]on_crash[>]/d" ${NAME}.xml
  sed -i -e "/[<]domain/a\\  <on_reboot>preserve</on_reboot>\\n" ${NAME}.xml
  sed -i -e "/[<]domain/a\\  <on_crash>preserve</on_crash>\\n" ${NAME}.xml
fi

# XXX roth -- HACK HACK HACK
# update the CPU type for xbs4 (Skylake)
if true; then
  if grep -q Broadwell ${NAME}.xml; then
    sed -i -e "s/Broadwell/Nehalem/" ${NAME}.xml
  fi
fi

virsh define ${NAME}.xml

echo "Starting VM"
virsh start --console $NAME
exit 0
