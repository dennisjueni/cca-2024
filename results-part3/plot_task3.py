import sys
from typing import Dict, List
import numpy as np
import json
from datetime import datetime, timedelta


time_format = "%Y-%m-%dT%H:%M:%SZ"


def main():

    runs = ["run1", "run2", "run3"]

    calculate_execution_time(runs)


def calculate_execution_time(runs: List[str]):


    total_time_name = "total_time"
    total_exec_time: Dict[str, List[timedelta]] = {}

    for run in runs:

        results_file = open(f"results-part3/final_runs/{run}/results.json", "r")
        json_file = json.load(results_file)

        start_times = []
        completion_times = []

        for item in json_file["items"]:
            name = item["status"]["containerStatuses"][0]["name"]
            if str(name) != "memcached":
                try:
                    start_time = datetime.strptime(
                        item["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"], time_format
                    )
                    completion_time = datetime.strptime(
                        item["status"]["containerStatuses"][0]["state"]["terminated"]["finishedAt"], time_format
                    )

                    if name in total_exec_time.keys():
                        total_exec_time[name].append(completion_time - start_time)
                    else:
                        total_exec_time[name] = [completion_time - start_time]

                    start_times.append(start_time)
                    completion_times.append(completion_time)

                except KeyError:
                    print("Job {0} has not completed....".format(name))
                    sys.exit(0)
    
        if total_time_name in total_exec_time.keys():
            total_exec_time[total_time_name].append(max(completion_times) - min(start_times))
        else:
            total_exec_time[total_time_name] = [max(completion_times) - min(start_times)]

        results_file.close()

    for key, values in total_exec_time.items():

        if len(values) != 3:
            print("Somehow not 3 runs were completed for job: ", key)

        exec_time_in_sec = [x.total_seconds() for x in values]
        mean = np.mean(exec_time_in_sec)
        std = np.std(exec_time_in_sec)

        if key == total_time_name:
            print(f"total time & {mean:.2f} & {std:.2f} \\\\  \\hline")
        else:
            print(f"\\coloredcell{{{key.removeprefix("parsec-")}}} & {mean:.2f} & {std:.2f} \\\\  \\hline")
        # print(f"{key}: mean = {mean:.2f}, std = {std:.2f}")


if __name__ == "__main__":
    main()
