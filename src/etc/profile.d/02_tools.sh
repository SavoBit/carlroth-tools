##############################
#
# 02_tools.sh
#
##############################

source=${BASH_SOURCE[0]}
sourcedir=${source%/*}
bindir=$(cd $sourcedir && cd ../../bin && pwd)
addpath PATH $bindir

prependpath $HOME/bin

unset source sourcedir bindir
return 0
