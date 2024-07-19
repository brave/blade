#!/bin/bash

# Note:   Collect SW-based measurements from an Android device
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         (original code from Matteo Varvello at Brave Software)
# Date:   05/03/2023

if [ $# -ne 4 ]
then
	echo "====================================================="
	echo "USAGE: $0 device-id sleep-time sw-power output-file"
	echo "====================================================="
	exit -1
fi
device_id=$1
sleep_time=$2
sw_power_enabled=$3
output_file=$4


# csv header
echo "timestamp,current,voltage,cpu_util" > "$output_file"

# start collecting data from the device via adb
while true
do
	timestamp=`date +%s.%N`  # local timestamp (not adb)

	cpu=`adb -s $device_id shell cat /proc/stat | head -n 1 | awk -v prev_total=$prev_total -v prev_idle=$prev_idle '{idle=$5; total=0; for (i=2; i<=NF; i++) total+=$i; print (1-(idle-prev_idle)/(total-prev_total))*100"%\t"idle"\t"total}'`
	if [ $? -ne 0 ]  # break if an error occurs
	then
		echo "ERROR: adb command failed"
		exit -1
	fi

	cpu_util=`echo "$cpu" | cut -f 1 | cut -f 1 -d "%"`
	prev_idle=`echo "$cpu" | cut -f 2`
	prev_total=`echo "$cpu" | cut -f 3`

	if [ $sw_power_enabled = "1" ]
	then
		power=`adb -s $device_id shell cat "sys/class/power_supply/*/uevent" | grep "CURRENT_NOW\|VOLTAGE_NOW" | head -n 2 | awk -v t=$timestamp 'BEGIN{ans=t} {split($1, A, "="); ans=ans","A[2]; }END{print ans}'`
		if [ $? -ne 0 ]  # break if an error occurs
		then
			echo "ERROR: adb command failed"
			exit -1
		fi
	else
		power="$timestamp,-1,-1"
	fi

	echo $power","$cpu_util >> "$output_file"

	sleep $sleep_time
done

# Explanation:
# https://stackoverflow.com/questions/23367857/accurate-calculation-of-cpu-usage-given-in-percentage-in-linux
