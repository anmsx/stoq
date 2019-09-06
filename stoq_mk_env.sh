user="$USER"
p="$HOME/stoq-dev-bkp"
pgit="$HOME/stoq-dev-git"
pgit="$HOME/stoqgithub/stoq"
#gitrep="http://gitlab.com/anmsx/stoq_src.git"
gitrep="http://github.com/anmsx/stoq.git"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

mkdir $p

mv /usr/share/stoq "$p/stoq"
mv /usr/share/stoqserver "$p/stoqserver"
mv /usr/local/lib/python3.6/dist-packages/stoq-3.2.0rc1-py3.6.egg/stoqlib "$p/stoqlibdist"
mv /usr/local/lib/python3.6/dist-packages/stoq-3.2.0rc1-py3.6.egg/stoq    "$p/stoq_lib"

#git clone $gitrep $pgit

ln -s "$pgit/data"        /usr/share/stoq 
#ln -s "$pgit/stoqserver"  /usr/share/stoqserver 
ln -s "$pgit/stoqlib"     /usr/local/lib/python3.6/dist-packages/stoq-3.2.0rc1-py3.6.egg/stoqlib 
ln -s "$pgit/stoq"        /usr/local/lib/python3.6/dist-packages/stoq-3.2.0rc1-py3.6.egg/stoq 


chown -R $user $pgit/*
chown -R $user $pgit/.git
