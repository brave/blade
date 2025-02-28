#!/bin/bash

set -e

if [ $# -ne 1 ]
then
	echo "========================================================="
	echo "USAGE: $0 device-id"
	echo "========================================================="
	exit -1
fi
device_id=$1

vncserver :1 -geometry 1280x720
websockify --web=/usr/share/novnc/ 6080 localhost:5901 &
scrcpy -s $device_id &
