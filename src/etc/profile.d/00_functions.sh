##############################
#
# shell functions
#
##############################

CMD=functions

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

unset CMD
return 0
