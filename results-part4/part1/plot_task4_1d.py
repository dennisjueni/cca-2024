import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.patches import Patch


MEASURE_DIR = "./results-part4/part1/final_run_d/"
QPS_MIN = 0
QPS_MAX = 130_000

labels = {0: "1 core, 2 threads", 1: "2 cores, 2 threads"}

suffix = {0: "1C_2T_CPU", 1: "2C_2T_CPU"}

for i in range(2):
    fig, ax1 = plt.subplots()
    qps = []
    p95 = []
    xs = []
    ys = []
    target = []
    xerr = []
    yerr = []
    groups_y = {}
    groups_x = {}
    cpu_usage = []
    for j in range(1):
        file_path = MEASURE_DIR + f"{suffix[i]}/run_{j}/mcperf.txt"
        file = open(file_path, "r")
        lines = file.read().splitlines()
        lines = [line.split() for line in lines]
        lines = [line for line in lines if len(line) == 20][1:]

        file_path = MEASURE_DIR + f"{suffix[i]}/run_{j}/cpu_utils.txt"
        file = open(file_path, "r")
        cpu_lines = file.read().splitlines()
        cpu_lines = [line.split() for line in cpu_lines]

        qps = qps + [float(line[-4]) for line in lines]
        target = target + [float(line[-3]) for line in lines]
        cpu_usage = []
        for l in lines:
            start = datetime.utcfromtimestamp(int(l[-2]) / 1000)
            end = datetime.utcfromtimestamp(int(l[-1]) / 1000)
            count = 0
            for cpu_l in cpu_lines:
                time = datetime.fromisoformat(cpu_l[0])

                if time <= start:
                    continue
                if time > end:
                    break
                if count != 0:
                    count += 1
                    continue
                if i == 0:
                    cpu_usage.append([float(cpu_l[4])])
                else:
                    cpu_usage.append([float(cpu_l[3]) + float(cpu_l[4])])
                break

        p95 = p95 + [float(line[-8]) / 1000 for line in lines]

    legend_elements = [
        Patch(facecolor="royalblue", label="P95", hatch="o", linestyle="-"),
        Patch(facecolor="orange", label="CPU"),
    ]

    ax1.plot(qps, p95, color="royalblue", label="P95", marker="o")
    ax1.set_ylabel("p95 tail latency [ms]", color="royalblue")
    ax1.tick_params(axis="y", labelcolor="royalblue")
    ax1.set_ylim([0, max(p95) + 0.5])
    ax1.hlines(1, QPS_MIN, QPS_MAX, color="k", linestyles="--")
    ax1.set_xticks(np.arange(0, 130_000 + 1, 26000))
    ax1.grid(True, which="both")
    ax1.set
    ax2 = ax1.twinx()
    ax2.plot(qps, cpu_usage, color="orange", label="CPU", marker="x")
    ax2.set_ylabel("CPU utilization [%]", color="orange")
    ax2.tick_params(axis="y", labelcolor="orange")
    if i == 0:
        ax2.set_ylim([0, 110])
    else:
        ax2.set_ylim([0, 210])

    plt.title(f"P95 Tail Latency and CPU Utsilization vs QPS for {labels[i]}")
    plt.xlim(QPS_MIN, QPS_MAX)
    plt.legend(handles=legend_elements)
    ax1.set_xlabel("QPS")
    plt.savefig(fname=f"test_{suffix[i]}.pdf")
    plt.close()
    # plt.errorbar(xs, ys, xerr=xerr, yerr=yerr, label = labels[i], capsize=3)
# plt.xlabel("QPS")
# plt.ylabel("p95 latency [ms]")
# plt.hlines(1, xmin=QPS_MIN, xmax=QPS_MAX, color='k', linestyles='--')
# plt.xlim(QPS_MIN, QPS_MAX)
# plt.legend()

# plt.title("P95 latency vs. QPS for Different Number of Threads and Cores")
