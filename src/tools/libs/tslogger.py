# Note:   Log timestamps and custom provided metrics to a json file
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   13/12/2024

import time
import json

from datetime import datetime


class TSLogger:

    def __init__(self, filename, metrics_headers=[]):

        # check if filename is provided and if is json
        if filename is None or len(filename) == 0 or not filename.endswith(".json"):
            raise Exception("Filename must be provided and be a json file")

        self.data = {}
        self.incomplete_data = {}
        self.metrics_headers = metrics_headers
        self.filename = filename

        # save empty data to file
        self.save()


    def log_begin(self, stage, metrics_dict={}, replace_if_exist=False):
        # log the beginning of a stage. metrics_dict should contain the metrics that will be logged at the end of the stage
        # and should be the same originally added in the metrics_headers list when creating the TSLogger object. Additional
        # metrics, not provided in the metrics_header will be ignored.

        time_start = time.time()

        if replace_if_exist == False and (stage in self.incomplete_data.keys() or stage in self.data.keys()):
            raise Exception(f"Stage '{stage}' already exists")
        
        # build entry
        stage_entry = {
            "time_start": time_start,
        }
        for metric in self.metrics_headers:
            if metric not in metrics_dict.keys():
                raise Exception(f"Metric '{metric}' not in metrics_dict")
            stage_entry[f"{metric}_start"] = metrics_dict[metric]

        # add entry to incomplete_data
        self.incomplete_data[stage] = stage_entry

    def log_end(self, stage, metrics_dict={}):
        # log the end of a stage.

        time_end = time.time()

        # pop entry from incomplete_data, and compute timings
        stage_entry = self.incomplete_data.pop(stage, None)
        if stage_entry is None:
            raise Exception(f"Stage '{stage}' does not exist")

        time_start = stage_entry["time_start"]
        duration = time_end - time_start

        # print stage info
        time_start_str = datetime.fromtimestamp(time_start).strftime('%H:%M:%S')
        time_end_str = datetime.fromtimestamp(time_end).strftime('%H:%M:%S')
        print(f"- Stage '{stage}' ended: {time_start_str} - {time_end_str} ({duration:.2f}s)")

        # add timing metrics
        stage_entry["time_end"] = time_end
        stage_entry["duration"] = duration

        # add other metrics
        for metric in self.metrics_headers:
            if metric not in metrics_dict.keys():
                raise Exception(f"Metric '{metric}' not in metrics_dict")
            stage_entry[f"{metric}_end"] = metrics_dict[metric]
            stage_entry[f"{metric}_diff"] = stage_entry[f"{metric}_end"] - stage_entry[f"{metric}_start"]
        
        self.data[stage] = stage_entry
        self.save()
    
    def save(self):

        # save self.data dict to file
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, sort_keys=True)
