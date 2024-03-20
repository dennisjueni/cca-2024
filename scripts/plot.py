from itertools import cycle
import sys
import pandas as pd
import re, os
from typing import Iterable, List, Tuple
import numpy as np
from pandas import DataFrame
import matplotlib.pyplot as plt
import seaborn as sns

MARKERS = ["o", "v", "^", "<", ">", "s", "p", "*", "h", "H", "D", "d", "P", "X"]


def load_run_data(file_path: str) -> pd.DataFrame:
    with open(file_path, "r") as f:
        lines = [line for line in f.readlines() if re.match(r"^(\#type|read)", line)]
        keys = lines[0].split()[1:]
        data = {k: [] for k in keys}
        for line in lines[1:]:
            line_values = line.split()[1:]
            for i, key in enumerate(keys):
                if key not in ["QPS", "target"]:
                    data[key].append((line_values[i] if i == 0 else float(line_values[i]) / 1e3))  # convert µs to ms
                else:
                    data[key].append(line_values[i] if i == 0 else float(line_values[i]))
    df = pd.DataFrame(data)
    return df


def load_run_data_folder(folder_path: str) -> List[pd.DataFrame]:
    return [load_run_data(os.path.join(folder_path, file)) for file in os.listdir(folder_path) if file.endswith(".txt")]


def get_mean_std(df_itr: Iterable[DataFrame], key: str) -> Tuple[np.ndarray, np.ndarray]:
    """Get mean and std of a key from a list of dataframes.

    Args:
    df_itr: Iterable[DataFrame] : List of dataframes to average / compute std over
    key: str : Key to index columns of dataframes
    """
    mean = np.mean(np.array([df[key] for df in df_itr]), axis=0)
    std = np.std(np.array([df[key] for df in df_itr]), axis=0)
    return mean, std


def plt_setup(xlim, ylim, title=None, xlabel=None, ylabel=None):
    sns.set_palette("deep")
    sns.set_style("whitegrid")
    plt.figure(figsize=(12, 8), dpi=150)
    plt.rcParams["font.size"] = 12
    plt.rcParams["font.family"] = "Arial"
    plt.grid(linestyle="--", linewidth=0.5, color="gray", which="both", alpha=0.5)
    sns.despine(left=True, bottom=True)
    plt.xlim(xlim)
    plt.ylim(ylim)
    # set ticks on x axis to every 5000
    plt.xticks(np.arange(0, xlim[1], 5000), labels=[f"{int(i//1000)} k" for i in np.arange(0, xlim[1], 5000)])
    plt.xlabel(xlabel or "QPS [queries/s]", labelpad=10, fontsize=12)  # Adjust labelpad and fontsize
    plt.ylabel(ylabel or "Latency [ms] 95th Percentile", labelpad=10, fontsize=12)
    plt.title(title or "Latency 95th Percentile wrt. QPS", pad=10, fontsize=12)


def plot_errorbar(x, y, xerr, yerr, label, color="black", marker="o"):
    plt.errorbar(x=x, y=y, xerr=xerr, yerr=yerr, fmt=marker, color=color, ecolor=color, elinewidth=2, alpha=0.7)
    plt.plot(x, y, marker, label=label, color=color, alpha=1, markersize=5, linestyle=":")


if __name__ == "__main__":
    while not os.path.exists("scripts"):
        os.chdir("../")
    # check if --task1 flag is present
    if "--task1" in sys.argv:
        plt_setup(xlim=(0, 55e3 + 1), ylim=(0, 8))
        colors = cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])
        benchmarks = [b for b in os.listdir("results") if os.path.isdir(f"results/{b}")]
        for i, benchmark in enumerate(benchmarks):
            dfs = load_run_data_folder(f"results/{benchmark}")
            p95_mean, p95_std = get_mean_std(dfs, "p95")
            qps_mean, qps_std = get_mean_std(dfs, "QPS")
            plot_errorbar(
                qps_mean,
                p95_mean,
                qps_std,
                p95_std,
                marker=MARKERS[i % len(MARKERS)],
                label=f"{benchmark}",
                color=next(colors),
            )
        plt.legend(loc="upper right")
        # plt.subplots_adjust(bottom=0.15)
        plt.subplots_adjust(left=0.08, right=0.92, bottom=0.08, top=0.95)
        plt.savefig("results/latency_95th_percentile_qps_part1.png")
        plt.show()
    else:
        print("Please provide a valid flag")
        sys.exit(1)
