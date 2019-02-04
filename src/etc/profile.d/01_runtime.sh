##############################
#
# compute a suitable runtime for e.g. sockets
#
# Compute a (temporary file) runtime directory
# that persists across multiple logins
#
# (Here, slightly violates XDG in that it is not
# guaranteed to be deleted on logout)
#
# Do *not* use $TMPDIR on MacOS, since the path
# is too long to store UNIX domain sockets of any reasonable length
#
##############################

if test -d "$SOCKET_RUNTIME_DIR"; then
  :
else
  set dummy /tmp/runtime-$(id -u)-*
  if test -d "$2" -a -w "$2"; then
    SOCKET_RUNTIME_DIR=$2
  else
    SOCKET_RUNTIME_DIR=$(mktemp -d /tmp/runtime-$(id -u)-XXXXXX)
  fi
  export SOCKET_RUNTIME_DIR
fi

