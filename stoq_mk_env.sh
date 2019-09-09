user="tds" # "$USER"
p="$HOME/stoq-dev-bkp"
pgit="$HOME/stoq-dev-git"
pgit="$HOME/stoq/stoq"
#gitrep="http://gitlab.com/anmsx/stoq_src.git"
gitrep="http://github.com/anmsx/stoq.git"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

mkdir $p

mv /usr/share/stoq "$p/stoq"
mv /usr/share/stoqserver "$p/stoqserver"
mv /usr/lib/python3.6/dist-packages/stoqlib "$p/stoqlibdist"
mv /usr/lib/python3.6/dist-packages/stoq    "$p/stoq_lib"

#git clone $gitrep $pgit

ln -s "$pgit/data"        /usr/share/stoq 
#ln -s "$pgit/stoqserver"  /usr/share/stoqserver 
#ln -s "$pgit/stoqlib"     /usr/lib/python3.6/dist-packages/stoq-3.1.0.egg-info/stoqlib 
#ln -s "$pgit/stoq"        /usr/lib/python3.6/dist-packages/stoq-3.1.0.egg-info/stoq 
ln -s "$pgit/stoqlib"     /usr/lib/python3.6/dist-packages/stoqlib 
ln -s "$pgit/stoq"        /usr/lib/python3.6/dist-packages/stoq 


chown -R $user $pgit/*
chown -R $user $pgit/.git
