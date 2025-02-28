#!/usr/bin/python3

# Note:   Collect memory measurements (PSS and RSS, in kilobytes) per app, using the dumpsys meminfo tool
# Author: Artem Chaikin (achaikin@brave.com)
# Date:   21/11/2024

import subprocess
import time
import csv
import argparse

from libs import constants

# Set up argument parsing
parser = argparse.ArgumentParser(description="Monitor Android app memory usage.")
parser.add_argument("device_id", help="The serial number of the connected device.")
parser.add_argument("package_name", help="The package name of the Android app to monitor.")
parser.add_argument("output", help="Output CSV file name.")
parser.add_argument("-i", "--interval", type=int, default=constants.ONE_SECOND*1000, help="Time interval (in milliseconds) between memory checks. Default is 1000 ms.")
args = parser.parse_args()

# Assign arguments to variables
device_id = args.device_id
package_name = args.package_name
output_file = args.output
interval_ms = args.interval  # Interval in milliseconds

# Open CSV file for logging
with open(output_file, "w", newline="") as csvfile:
    fieldnames = ["timestamp", "pss", "rss"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    while True:
        try:
            # Run adb command to get memory info
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "dumpsys", "meminfo", package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            epoch_timestamp = int(time.time() * 1000)  # Get current time in milliseconds

            # Parse PSS and RSS totals
            pss_total = rss_total = None
            lines = result.stdout.splitlines()
            for line in lines:
                if "TOTAL PSS:" in line and "TOTAL RSS:" in line:
                    parts = line.split()
                    try:
                        pss_total = int(parts[2])  # Extract the value after "TOTAL PSS:"
                        rss_total = int(parts[5])  # Extract the value after "TOTAL RSS:"
                    except (IndexError, ValueError):
                        continue

            # Log to CSV if data is found
            if pss_total is not None and rss_total is not None:
                writer.writerow({"timestamp": epoch_timestamp, "pss": pss_total, "rss": rss_total})
                csvfile.flush()

            # Wait for the specified interval in milliseconds
            time.sleep(interval_ms / 1000.0)

        except subprocess.CalledProcessError:
            # Continue if there are issues running adb
            continue
        
        except KeyboardInterrupt:
            # Stop monitoring when interrupted
            break
