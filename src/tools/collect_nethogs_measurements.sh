#!/bin/bash

# Note:   Collect bandwidth measurements (sent/received, in bytes) per app, using the nethogs tool
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   07/09/2023

set -e

if [ $# -ne 3 ]
then
	echo "========================================================="
	echo "USAGE: $0 device-id delay output-file"
	echo "========================================================="
	exit -1
fi
device_id=$1
delay=$2
output_file=$3

# path to nethogs within the Android device (need to be rooted)
NETHOGS_PATH="/data/local/tmp/nethogs"

# csv header
echo "timestamp,package,sent,received" > "$output_file"

# start measurements
adb -s $device_id shell "su -c /data/local/tmp/nethogs -t -d $delay -v 3" | grep --line-buffered "com." | unbuffer -p awk -F '\t' 'BEGIN{ OFS="," } { print systime(),$1,$2,$3 }' >> "$output_file"
