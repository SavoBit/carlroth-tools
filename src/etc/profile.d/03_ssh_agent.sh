#!/bin/bash
#
######################################################################
#
# ssh_agent
#
# normalize the ssh-agent
#
# Emit SSH_AUTH_SOCK etc. for shell scripts
#
######################################################################

CMD=ssh_agent

agent_sock=$(gpgconf --list-dirs | grep ^agent-socket: | cut -d: -f2)
agent_ssh_sock=$(gpgconf --list-dirs | grep ^agent-ssh-socket: | cut -d: -f2)
if test "$agent_ssh_sock"; then
  :
else
  agent_ssh_sock=${agent_sock}.ssh
fi

# this may be from a forwarded gpg-agent connection (socket or file)
if test -e "$agent_sock"; then
  agent_pid=$(gpg_agent_valid $agent_sock)
  if test -z "$agent_pid"; then
    echo "$CMD: *** invald gpg-agent socket $agent_sock" 1>&2
  fi
fi

if test -S "$SSH_AUTH_SOCK"; then
  sock_real=$(realpath $SSH_AUTH_SOCK)
else
  sock_real=
fi

##############################
#
# see if gpg-agent should supercede ssh-agent,
# but only for local sessions
#
##############################

if test_ssh_client; then
  loginmsg "$CMD: ssh-agent is being provided remotely ($SSH_AUTH_SOCK)"
elif test -S "$agent_ssh_sock"; then

  if test "$sock_real" -ef "$agent_ssh_sock"; then
    :
  else
    loginmsg "$CMD: ssh-agent is being provided by a local gpg-agent"
    loginmsg "$CMD: deprecating agent $SSH_AUTH_SOCK"
    sock_real=$(realpath $agent_ssh_sock)
  fi

  if test "$agent_pid" -a "$agent_pid" != "-1"; then
    SSH_AGENT_PID=$agent_pid
    export SSH_AGENT_PID
  fi

fi

##############################
#
# Normalize the ssh-agent socket location so that it can be
# shared with containers (and docker-machine)
#
# NOTE that this will also include forwarded ssh-agent connections
#
##############################

if test "$sock_real"; then

  # ok to move/link the socket, but keep it on the same filesystem
  # Also avoid $TMPDIR on MacOS because long pathnames
  sshdir=${sock_real%/*}
  sock_fs=$(stat_d ${sshdir})

  runtime_fs=$(stat_d ${SOCKET_RUNTIME_DIR} 2>/dev/null)

  if test $sock_fs = $runtime_fs; then
    sshruntime=$SOCKET_RUNTIME_DIR
    sshruntime_fs=$runtime_fs
  else
    sshruntime=$sshdir
    sshruntime_fs=$sock_fs
  fi

  if test $sock_fs == $sshruntime_fs; then
    if test "$SSH_CONNECTION"; then
      set dummy $SSH_CONNECTION
      for ck in $(echo $2 $3 | cksum); do break; done
      sock_canon=${sshruntime}/ssh/agent-${ck}
    else
      # local ssh-agent, do not canonicalize
      sock_canon=$sock_real
    fi
    if test $sock_real -ef $sock_canon; then
      sock_real=$sock_canon
    elif ssh_agent_valid $sock_canon; then
      echo "$CMD: *** agent $sock_canon is in the way" 1>&2
    else
      loginmsg "$CMD: linking agent $sock_real --> $sock_canon"
      mkdir -p ${sshruntime}/ssh
      rm -f $sock_canon
      ln $sock_real $sock_canon
      sock_real=$sock_canon
      # hard-link, not symlink
    fi
  else
    echo "$CMD: *** ssh agent at $sock_real cannot be moved/linked" 1>&2
  fi

  if ssh_agent_valid $sock_real; then
    SSH_AUTH_SOCK=$sock_real
  else
    echo "$CMD: *** invalid agent $sock_real" 1>&2
    sock=$(ssh_agent_find $sshruntime)
    if test "$sock"; then
      SSH_AUTH_SOCK=$sock
    fi
  fi

fi

if test_ssh_client; then
  ssh_agent_clean $sshruntime
fi

# compute a friendly symlink
if test -S "$SSH_AUTH_SOCK"; then

  # detect containers
  cid=$(container-id 2>/dev/null)
  if test "$cid"; then
    sock_link=${sshruntime}/ssh/agent-docker-${cid}
  elif test "$SSH_AUTH_SOCK" -ef "$agent_ssh_sock"; then
    sock_link=${sshruntime}/ssh/agent-gpg
  elif test "$SSH_CONNECTION"; then
    set dummy $SSH_CONNECTION
    sock_link="${sshruntime}/ssh/agent-${2}"
    sock_link=${sock_link//:/-}
    sock_link=${sock_link//[.]/-}
  else
    sock_link=${sshruntime}/ssh/agent
  fi

  if symlink $SSH_AUTH_SOCK $sock_link; then
    export SSH_AUTH_SOCK=$sock_link
  fi

  # put a friendly link in $HOME
  if symlink $SSH_AUTH_SOCK $HOME/.ssh/agent-socket; then
    export SSH_AUTH_SOCK=$HOME/.ssh/agent-socket
  fi

  unset cid sock_link
fi

unset agent_sock agent_ssh_sock agent_pid
unset sock_real
unset sshruntime

unset CMD

return 0
