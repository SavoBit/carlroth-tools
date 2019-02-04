##############################
#
# shell functions
#
##############################

addpath()
{
  local var val
  var=$1; shift
  val=$1; shift

  case ":${!var}:" in
    *:"$val":*) ;;
    *)
      eval $var=\"${!var}:$val\"
    ;;
  esac
}

prependpath()
{
  local var val
  var=$1; shift
  val=$1; shift

  case ":${!var}:" in
    *:"$val":*) ;;
    *)
      eval $var=\"$val:${!var}\"
    ;;
  esac
}

case "$(uname -s)" in
  Linux)
    stat_d() {
      stat -c "%d" "$1"
    }
    # ha ha suckers, not every version of coreutils has 'realpath'
    if test -x /usr/bin/realpath; then
      :
    else
      realpath() {
        python -c "import os, sys; print os.path.realpath(sys.argv[1]);" "$@"
      }
    fi
  ;;
  Darwin)
    realpath() {
      python -c "import os, sys; print os.path.realpath(sys.argv[1]);" "$@"
    }
    stat_d() {
      stat -f "%d" "$1"
    }
  ;;
esac

ssh_agent_valid()
{
  local sock sts
  sock=$1; shift

  env SSH_AUTH_SOCK=$sock ssh-add -l 1>/dev/null 2>&1
  sts=$?

  test $sts -eq 0 && return 0
  # non-empty key list

  test $sts -eq 1 && return 0
  # empty key list, still OK

  return 1
}

# find a working ssh-agent
# grovel through the ssh runtime dir to find a valid socket
ssh_agent_find()
{
  local runtime pat sock failed
  runtime=$1; shift

  set dummy $SSH_CONNECTION
  sock_pat="${runtime}/ssh/agent-${2}-*"

  # prefer one from the same connecting client
  for sock in $(/bin/ls -1t $sock_pat 2>/dev/null); do
    if ssh_agent_valid $sock; then
      echo "$CMD:$FUNCNAME: found client agent $sock" 1>&2
      echo $sock
      return 0
    fi
  done

  for sock in $(/bin/ls -1t ${sshruntime}/ssh 2>/dev/null); do
    if ssh_agent_valid ${sshruntime}/ssh/$sock; then
      echo "$CMD: found non-client agent $sock" 1>&2
      echo $sock
      return 0
    fi
  done

  return 1
}

ssh_agent_clean()
{
  local runtime p tgt
  runtime=$1; shift

  for p in $runtime/ssh/*; do
    test -L "$p" && continue
    if test -S $p; then
      if ssh_agent_valid $p; then
        :
      else
        echo "$CMD:$FUNCNAME: socket $p is stale" 1>&2
        rm $p
      fi
    fi
  done
  for p in $sshruntime/ssh/*; do
    if test -L $p; then
      tgt=$(readlink $p)
      if test -e "$tgt"; then
        :
      else
        echo "$CMD:$FUNCNAME: symlink $p --> $tgt is stale" 1>&2
        rm $p
      fi
    fi
  done
}

gpg_agent_valid()
{
  local sock pid
  sock=$1; shift

  set dummy $(gpg-connect-agent -S "$sock" "getinfo pid" /bye 2>/dev/null)
  if test "$2" = "D"; then
    pid=$3
    if ps -p $pid 1>/dev/null 2>&1; then
      echo $pid
      return 0
    else
      # reports a PID but it is wrong
      echo -1
      return 0
    fi
  fi

  set dummy $(gpg-connect-agent -S "$sock" "nop" /bye 2>/dev/null)
  if test "$2" = "OK"; then
    echo -1
    return 0
  fi

  return 1
}

test_loginshell()
{
  local buf

  buf=$(shopt login_shell 2>&1)
  case "$buf" in
    *on*) return 0 ;;
    *off*) return 1 ;;
  esac

  buf=$(cat /proc/$$/comm 2>&1)
  case "$buf" in
    -*) return 0 ;;
  esac
  
  buf=$(ps -p $$ -o comm= 2>&1)
  case "$buf" in
    -*) return 0 ;;
  esac

  return 1
}

test_ssh_client()
{
  local ppid buf comm

  test "$SSH_CLIENT" || return 1

  ppid=$(ps -p $$ -o ppid=)

  buf=$(cat /proc/$ppid/comm 2>&1)
  case "$buf" in
    sshd) return 0 ;;
  esac
  
  buf=$(ps -p $ppid -o comm= 2>&1)
  case "$buf" in
    sshd) return 0 ;;
  esac

  return 1
}

loginmsg()
{
  test_loginshell || return 0
  echo "$@"
  return 0
}
