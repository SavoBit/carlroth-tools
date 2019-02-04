##############################
#
# configure a local cache directory
#
##############################

##############################
#
# Compute a suitable cache directory for ccache
#
##############################

if test "$CACHE_HOME"; then
  :
else
  case "$(uname -s)" in
    Darwin)
      CACHE_HOME=${CACHE_HOME-"${HOME}/Library/Caches"}
    ;;
    Linux)
      if test ${CACHE_HOME+set}; then
        :
      else
        if grep -q docker /proc/self/cgroup; then
          if test -d "${HOME}/Library/Caches"; then
            CACHE_HOME=${HOME}/Library/Caches
          else
            CACHE_HOME=${XDG_CACHE_HOME-"${HOME}/.cache"}
          fi
        else
          CACHE_HOME=${XDG_CACHE_HOME-"${HOME}/.cache"}
        fi
      fi
    ;;
    *)
      CACHE_HOME=${CACHE_HOME-"${HOME}/tmp"}
    ;;
  esac
fi

# See
# http://git.buildroot.net/buildroot/commit/?id=433290761fceb476b095548eec10adf72405e050
export CCACHE_DIR=${CACHE_HOME}/ccache
export BR2_CCACHE_DIR=${CACHE_HOME}/buildroot-ccache
export BUILDROOT_CACHE_DIR=${CACHE_HOME}/buildroot-ccache
prependpath PATH /usr/lib/ccache
