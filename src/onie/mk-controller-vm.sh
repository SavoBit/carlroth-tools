#!/bin/sh
#
######################################################################
#
# mk-controller-vm.sh
#
# similar to the switch light setup;
# except here the controller VM needs (really wants?)
# a host-mapped filesystem with a random seed, else the entropy
# gathering takes a long time.
#
# See also
# https://github.com/bigswitch/bvs/blob/master/src/main/hardware/kvm_bcf.xml
# https://github.com/bigswitch/bvs/blob/master/src/main/hardware/start_vm.sh
# https://landley.net/kdocs/Documentation/filesystems/9p.txt
# http://wiki.qemu.org/Documentation/9psetup
#
# also:
# # apt-get install 9mount
# # modprobe 9pnet_virtio
#
######################################################################

bindir=$(dirname $0)
bindir=$(cd $bindir && pwd)

NAME="controller-bcf-4.7"

MEM=1024
DISK="$PWD/controller.qcow"
SNAP="$PWD/controller-vda-snap.qcow"
IMG="$PWD/controller-vda.img"

# Path to OVMF firmware for qemu
# Download OVMF from http://www.tianocore.org/ovmf/
OVMF="$HOME/kvm/OVMF.fd"

# VM will listen on telnet port $KVM_PORT
# For BCF-4.2, this needs to be an emulated serial port
KVM_PORT=9001

# VNC display to use
VNC_PORT=3

MAC=52:54:00:9B:57:A8

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

if test "$NOIMG"; then
  echo "*** re-using existing disk images" 1>&2
else
  echo "generating disk images" 1>&2
  sudo rm -f $SNAP
  ##qemu-img create -o backing_file=$DISK -f qcow $SNAP

  sudo rm -f $IMG
  # once the VM is running it is owned by a root-ish user
  
  qemu-img convert -O raw $DISK $IMG || exit 1
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

mkdir -p $PWD/hostfiles/random
dd if=/dev/urandom of=$PWD/hostfiles/random/seed bs=1 count=128

virsh destroy "$NAME" || :
virsh undefine "$NAME" || :

# Tee hee, they disabled the libvirt disk driver but not the
# virtio-net driver...

OPTS=$OPTS${OPTS:+" "}"-r $MEM"
OPTS=$OPTS${OPTS:+" "}"-n $NAME"
OPTS=$OPTS${OPTS:+" "}"--disk path=$IMG,device=disk,format=raw"
OPTS=$OPTS${OPTS:+" "}"--network=bridge:br0,mac=$MAC,model=virtio"
OPTS=$OPTS${OPTS:+" "}"--import --noautoconsole"
OPTS=$OPTS${OPTS:+" "}"--graphics vnc,listen=0.0.0.0,password=bsn"

# enable the random seed
##OPTS=$OPTS${OPTS:+" "}"--fsdev local,id=roth_host0,path=$PWD/hostfiles,security_model=none"
##OPTS=$OPTS${OPTS:+" "}"--device virtio-9p-pci,id=virtio0,fsdev=roth_host0,mount_tag=/hypervisor-data"
OPTS=$OPTS${OPTS:+" "}"--filesystem $PWD/hostfiles,/hypervisor-data"

echo "Generating XML for $NAME"
virt-install --connect qemu:///system --print-xml $OPTS > ${NAME}.xml
sts=$?
test $sts -eq 0 || exit $sts

# update the crash/reboot behavior for debugging
if true; then
  sed -i -e "/[<]on_reboot[>]/d" ${NAME}.xml
  sed -i -e "/[<]on_crash[>]/d" ${NAME}.xml
  sed -i -e "/[<]domain/a\\  <on_reboot>preserve</on_reboot>\\n" ${NAME}.xml
  sed -i -e "/[<]domain/a\\  <on_crash>preserve</on_crash>\\n" ${NAME}.xml
fi

virsh define ${NAME}.xml

echo "Starting VM"
virsh start --console $NAME
exit 0
