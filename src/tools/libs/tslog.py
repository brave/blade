# Note:   Log timestamps to a csv file
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   10/03/2023

import time
from datetime import datetime

from libs import adblib


class TSLog:

    stages = {}

    def __init__(self, filename, device, connection):

        # open file and write header
        self.file = open(filename, "w", encoding="utf-8")
        self.file.write("stage,time_start,time_end,duration,rx,tx\n")
        self.device = device
        self.connection = connection

    def log_begin(self, stage):
        timestamp = time.time()

        # get device's rx and tx state (in bytes)
        rx, tx = adblib.get_device_traffic(self.device, self.connection)

        # print
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"- Begin: {stage} ({time_str})")

        if stage in self.stages:
            raise Exception(f"Stage {stage} already exists")

        self.stages[stage] = (timestamp, rx, tx)

    def log_end(self, stage):
        timestamp = time.time()

        # get device's rx and tx state (in bytes)
        rx, tx = adblib.get_device_traffic(self.device, self.connection)

        # print
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"- End: {stage} ({time_str})")

        if stage not in self.stages:
            raise Exception(f"Stage {stage} does not exist")

        time_start, rx_start, tx_start = self.stages.pop(stage)
        duration = timestamp - time_start
        rx = rx - rx_start
        tx = tx - tx_start
        self.file.write(
            f"{stage},{time_start},{timestamp},{duration},{rx},{tx}\n")
        self.file.flush()

    # close file
    def close(self):

        if len(self.stages) > 0:
            print(
                "WARNING: The following stages have not been ended: "
                + ", ".join(self.stages.keys())
            )

        self.file.close()
