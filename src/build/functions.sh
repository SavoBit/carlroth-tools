##############################
#
# common build functions
#
##############################

#!/bin/bash
set -e
set -x

bindir=$(dirname $0)
bindir=$(cd $bindir && pwd)

MAKE=docker-make

if grep -q BMF ${SWITCHLIGHT}/tools/version.py; then
  build_bmf=1
fi

do_build_common() {
  rm -fr ${SWITCHLIGHT}/submodules/loader/rootfiles/lib/platform-config
  rm -fr ${SWITCHLIGHT}/submodules/loader/buildroot-${ARCH}/target/lib/platform-config

  local odir
  odir=$PWD
  cd ${SWITCHLIGHT}/components/all/platform-config
  set dummy $(git ls-files */Makefile)
  cd $odir
  shift
  while test $# -gt 0; do
    local mf plat
    mf=$1; shift
    plat=${mf%/Makefile}
    case "$plat" in
      *-common) ;;
      ${ARCH3}-*)
        ${MAKE} -C ${SWITCHLIGHT}/components/all/platform-config/${plat} deb
      ;;
    esac
  done
  if test -f ${SWITCHLIGHT}/components/all/platform-config/${ARCH4}-common/Makefile; then
    ${MAKE} -C ${SWITCHLIGHT}/components/all/platform-config/${ARCH4}-common deb
  fi

  ${MAKE} -C ${SWITCHLIGHT}/components/all/vendor-config/switchlight deb
  ${MAKE} -C ${SWITCHLIGHT}/components/all/slrest/ deb
  ${MAKE} -C ${SWITCHLIGHT}/components/all/ztn/ deb
  ${MAKE} -C ${SWITCHLIGHT}/components/all/cli/ deb

  return 0
}

do_build_initrd() {
  rm -fr ${SWITCHLIGHT}/debian/installs/${ARCH}/buildroot-initrd
  ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/initrd/buildroot deb

  rm -fr ${SWITCHLIGHT}/debian/installs/${ARCH}/bcf-loader-initrd
  ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/initrd/bcf deb

  if test "$build_bmf"; then
    if test -f ${SWITCHLIGHT}/components/${ARCH2}/initrd/bmf/Makefile; then
      rm -fr ${SWITCHLIGHT}/debian/installs/${ARCH}/bmf-loader-initrd
      ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/initrd/bmf deb
    fi
  fi

  case "$ARCH" in
    powerpc)
      find ${SWITCHLIGHT}/components/${ARCH2}/fit -name 'initrd*' -print | xargs -i rm "{}"
      find ${SWITCHLIGHT}/components/${ARCH2}/fit -name '*.itb' -print | xargs -i rm "{}"
      # Hrm, initrd does not seem to be updating

      rm -fr ${SWITCHLIGHT}/debian/installs/${ARCH}/bcf-fit
      ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/fit/bcf deb

      if test "$build_bmf"; then
        if test -f ${SWITCHLIGHT}/components/${ARCH2}/fit/bmf/Makefile; then
          rm -fr ${SWITCHLIGHT}/debian/installs/${ARCH}/bmf-fit
          ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/fit/bmf deb
        fi
      fi
      ;;
    x86_64)
      ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/upgrade/bcf deb
      if test "$build_bmf"; then
        if test -f ${SWITCHLIGHT}/components/${ARCH2}/upgrade/bmf/Makefile; then
          ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/upgrade/bmf deb
        fi
      fi
      ;;
  esac
}

do_build_broadcom() {
  $bindir/broadcom-regen
  ${MAKE} -C ${SWITCHLIGHT}/components/${ARCH2}/broadcom/ofad/ofad-6.3.3-internal-bcf deb
}

do_build_installer() {
  ${MAKE} -C ${SWITCHLIGHT}/builds/installer/${ARCH2}/bcf/ztn
  ${MAKE} -C ${SWITCHLIGHT}/builds/installer/${ARCH2}/bcf/ztn-ipv4

  if test "$build_bmf"; then
    if test -f ${SWITCHLIGHT}/builds/installer/${ARCH2}/bmf/netboot/Makefile; then
      ${MAKE} -C ${SWITCHLIGHT}/builds/installer/${ARCH2}/bmf/netboot
    fi
  fi

  # ugh, loader upgrade image stays stale
  rm -fr ${SWITCHLIGHT}/builds/swi/${ARCH2}/etc/boot.d/upgrade/${ARCH5}
}

do_build_swi() {
  rm -f ${SWITCHLIGHT}/builds/swi/${ARCH2}/${SWICFG}/*.swi
  rm -f ${SWITCHLIGHT}/builds/swi/${ARCH2}/${SWICFG}/rootfs/.rootfs-${ARCH2}.done
  sudo rm -fr ${SWITCHLIGHT}/builds/swi/${ARCH2}/${SWICFG}/rootfs/rootfs-${ARCH2}
  ${MAKE} -C ${SWITCHLIGHT}/builds/swi/${ARCH2}/${SWICFG}
}

do_stage_floodlight() {
  rm -f ${HOME}/work/controller/eclipse/appliance-dev/var/lib/floodlight/zerotouch/*.swi
  cp ${SWITCHLIGHT}/builds/swi/${ARCH2}/${SWICFG}/*_SWI.swi ${HOME}/work/controller/eclipse/appliance-dev/var/lib/floodlight/zerotouch/.
  rm -f ${HOME}/work/controller/eclipse/appliance-dev/var/lib/floodlight/zerotouch/*-INSTALLER
  cp ${SWITCHLIGHT}/builds/installer/${ARCH2}/bcf/ztn/*-INSTALLER ${HOME}/work/controller/eclipse/appliance-dev/var/lib/floodlight/zerotouch/.
}

do_build() {
  rm -f ${SWITCHLIGHT}/make/versions/*
  do_build_common
  do_build_initrd
  do_build_broadcom
  do_build_installer
  do_build_swi
  do_stage_floodlight
}

# Local variables:
# mode: sh
# sh-indentation: 2
# sh-basic-offset: 2
# End:
