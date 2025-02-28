#!/bin/bash

# Note:   Get network usage statistics for a specific app from phone.
# Author: Artem Chaikin (achaikin@brave.com)
# Date:   06/12/2024

# show script usage
if [ $# -ne 2 ]
then
    echo "===================================================="
    echo "USAGE: $0 device-id uid"
    echo "===================================================="
    exit -1
fi

device_id=$1
uid=$2

# get network usage in bytes for specific uid
function getUsagePerApp () 
{ 
    rx=$(adb -s $device_id shell dumpsys netstats | awk -v uid="$uid" '
        /mAppUidStatsMap:/ { found=1; next }
        found && $1 == uid { print $2; exit }
    ')
    
    tx=$(adb -s $device_id shell dumpsys netstats | awk -v uid="$uid" '
        /mAppUidStatsMap:/ { found=1; next }
        found && $1 == uid { print $4; exit }
    ')

    if [ -z "$rx" ] || [ -z "$tx" ]; then
        echo "No data found for UID $uid" >&2
        exit 1
    fi

    echo RX=$rx,TX=$tx
}

getUsagePerApp $device_id $uid 