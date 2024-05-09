import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.patches import Patch


MEASURE_DIR = "./results-part4/part1/final_run/"
QPS_MIN = 0
QPS_MAX = 130_000

labels = {0: "1 core, 2 threads", 1: "2 cores, 2 threads"}

suffix = {0: "1C_2T", 1: "2C_2T"}

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
                if count < 2:
                    count += 1
                    continue
                if i == 0:
                    cpu_usage.append([float(cpu_l[2])])
                else:
                    cpu_usage.append([float(cpu_l[3]) + float(cpu_l[2])])
                break

        p95 = p95 + [float(line[-8]) / 1000 for line in lines]

    legend_elements = [
        Patch(facecolor="#CC0A00", label="P95 latency"),
        Patch(facecolor="#00CCA0", label="CPU utilization"),
    ]

    ax1.plot(qps, p95, color="#CC0A00", label="P95", marker="x")
    ax1.set_ylabel("P95 Tail Latency (ms)", color="#CC0A00")
    ax1.tick_params(axis="y", labelcolor="#CC0A00")
    ax1.set_ylim([0, max(p95) + 0.5])
    ax1.hlines(1, QPS_MIN, QPS_MAX, color="k", linestyles="--")
    ax1.set_xlim(0, 130_000)
    ax1.set_xticks([0, 25000, 50000, 75000, 100000, 125000])
    ax1.set_xticklabels(["0", "25'000", "50'000", "75'000", "100'000", "125'000"])
    ax1.grid(True, which="both")
    ax1.set
    ax2 = ax1.twinx()
    ax2.plot(qps, cpu_usage, color="#00CCA0", label="CPU", marker="o")
    ax2.set_ylabel("CPU utilization (%)", color="#00CCA0")
    ax2.tick_params(axis="y", labelcolor="#00CCA0")
    if i == 0:
        ax2.set_ylim([0, 110])
    else:
        ax2.set_ylim([0, 210])

    plt.title(f"P95 Tail Latency and CPU Utsilization vs QPS for {labels[i]}")
    plt.xlim(QPS_MIN, QPS_MAX)
    plt.legend(handles=legend_elements)
    ax1.set_xlabel("QPS")
    plt.savefig(fname=f"{MEASURE_DIR}/plot_1d_{suffix[i]}.pdf")
    plt.close()
