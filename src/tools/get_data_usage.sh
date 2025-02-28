#!/bin/bash

# Note:   Get android network usage statistics from phone.
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         Based on the script from Zibri -- https://gist.github.com/Zibri/387f0bd0acf09f71384ce78dd45aa058
# Date:   28/06/2023

# show script usage
if [ $# -ne 1 ]
then
	echo "===================================================="
	echo "USAGE: $0 device-id"
	echo "===================================================="
	exit -1
fi
device_id=$1

# get network usage in bytes
function getUsage () 
{ 
    rb=0;
    tb=0;
    for a in $(adb -s $device_id shell dumpsys netstats|grep "rb="|cut -d "=" -f 3|cut -d " " -f 1);
    do
        rb=$((rb+a));
    done;
    rb=$((rb/2));
    for a in $(adb -s $device_id shell dumpsys netstats|grep "rb="|cut -d "=" -f 5|cut -d " " -f 1);
    do
        tb=$((tb+a));
    done;
    tb=$((tb/2));
    echo RX=$rb,TX=$tb;
};

getUsage $device_id
