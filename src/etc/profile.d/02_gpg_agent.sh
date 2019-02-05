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
if test "$SSH_CLIENT"; then
  for client in $SSH_CLIENT; do break; done
  for ck in $(echo $client | cksum); do break ;done
  sock_canon=$socketdir/S.gpg-agent.${ck}
else
  sock_canon=
fi

if test_ssh_client; then
  if test -S "$sock_remote"; then
    pid=$(gpg_agent_valid $sock_remote)
    if test "$pid"; then
      loginmsg "$CMD: staging remote gpg-agent (pid $pid, client $client) as $sock_canon"
      rm -f $sock_canon
      mv $sock_remote $sock_canon
    fi
  fi
  gpglink $sock_canon $sock
elif test "$SSH_CLIENT"; then
  :
elif test -S $sock -o -S $sock_local; then
  gpglink $sock_local $sock
fi

unset sock socketdir sock_local sock_remote sock_canon

unset CMD

return 0
