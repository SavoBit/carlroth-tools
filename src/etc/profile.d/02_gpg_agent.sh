##############################
#
# gpg_agent.sh
#
# clean up the gpg-agent socket usage
#
# 1. move the default gpg-agent socket out of the way
#    and replace it with an NFS stub
# 2. move any remote gpg-agent socket out of the way
#    (created by SSH RemoteForward)
#    and replace the default with its NFS stub
#
# no output required here; as of GnuPG 2.1 gpg-agent uses default paths always
#
######################################################################

CMD=gpg_agent

sock=$(gpgconf --list-dirs | grep ^agent-socket: | cut -d: -f2)
socketdir=$(gpgconf --list-dirs | grep ^socketdir: | cut -d: -f2)
if test "$socketdir"; then
  :
else
  socketdir=${sock%/*}
fi
if test -d "$socketdir"; then
  :
else
  gpgconf --create-socketdir
fi

sock_local=$socketdir/S.gpg-agent.local
sock_remote=$socketdir/S.gpg-agent.remote

# move the local gpg-agent socket out of the way
# and use a redirect file
if test -S "$sock"; then
  pid=$(gpg_agent_valid $sock)
  if test "$pid"; then
    loginmsg "$CMD: staging local gpg-agent (pid $pid)"
    rm -f $sock_local
    mv $sock $sock_local
    cp /dev/null $sock
    chmod 0600 $sock
    echo "%Assuan%" >> $sock
    echo "socket=$sock_local" >> $sock
  else
    echo "$CMD: *** invalid gpg-agent socket $sock" 1>&2
  fi
elif test -S $sock_local; then
  # Move the local gpg-agent back into position after a logout
  # Do this always; later on in this script we may update it
  # with the remote gpg-agent
  pid=$(gpg_agent_valid $sock_local)
  if test "$pid"; then
    if grep -q $sock_local $sock 2>/dev/null; then
      :
    else
      loginmsg "$CMD: restoring local gpg-agent (pid $pid)"
      cp /dev/null $sock
      chmod 0600 $sock
      echo "%Assuan%" >> $sock
      echo "socket=$sock_local" >> $sock
    fi
  else
    echo "$CMD: *** invalid gpg-agent socket $sock_local" 1>&2
    rm -f $sock_local
  fi
fi

##############################
#
# see if we created a remote socket while logging in
#
# NOTE that default forwarding behavior for SSH will
# *NOT* delete the socket if it already exists
#
##############################

if test ${SSH_CLIENT+set}; then
  if test -S "$sock_remote"; then
    loginmsg "$CMD: found a forwarded agent at $sock_remote"
    pid=$(gpg_agent_valid $sock_remote)
    if test "$pid"; then
      for client in $SSH_CLIENT; do break; done
      for ck in $(echo $client | cksum); do break ;done
      sock_canon=$socketdir/s.gpg-agent.${ck}
      loginmsg "$CMD: staging remote gpg-agent (pid $pid, client $client) as $sock_canon"
      rm -f $sock_canon
      mv $sock_remote $sock_canon
      if test -S "$sock"; then
        echo "$CMD: *** default gpg-agent socket is in the way" 1>&2
      elif ssh_agent_valid "$sock_canon"; then
        echo "$CMD: *** agent $sock_canon socket is in the way" 1>&2
        sock_canon=$sock_real
      else
        rm -f "$sock"
        loginmsg "$CMD: updating default gpg-agent socket"
        cp /dev/null $sock
        chmod 0600 $sock
        echo "%Assuan%" >> $sock
        echo "socket=$sock_canon" >> $sock
      fi
      unset client ck sock_canon
    else
      echo "$CMD: *** invalid remote gpg-agent socket $sock_remote" 1>&2
      rm -f $sock_remote
    fi
    unset pid
  else
    echo "$CMD: *** remote SSH connection did not provide a gpg-agent" 1>&2
  fi
fi

unset sock socketdir sock_local sock_remote
unset sock_real

unset CMD

return 0
