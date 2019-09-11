user="tds" # "$USER"
p="$HOME/stoq-dev-bkp"
pgit="$HOME/stoq-dev-git"
pgit="$HOME/stoq/stoq"
#gitrep="http://gitlab.com/anmsx/stoq_src.git"
gitrep="http://github.com/anmsx/stoq.git"

#if [[ $EUID -ne 0 ]]; then
#   echo "This script must be run as root"
#   exit 1
#fi

dh_builddeb
