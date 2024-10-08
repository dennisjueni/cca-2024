from itertools import cycle
import pandas as pd
import os
from typing import Iterable, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

MARKERS = ["o", "v", "^", "<", ">", "s", "p", "*", "h", "H", "D", "d", "P", "X"]

label_mapping = {
    "ibench-l1d": "iBench L1D",
    "ibench-l2": "iBench L2",
    "ibench-membw": "iBench MemBW",
    "no_interference": "No Interference",
    "ibench-l1i": "iBench L1I",
    "ibench-llc": "iBench LLC",
    "ibench-cpu": "iBench CPU",
}


def load_run_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, delimiter=" ", skipinitialspace=True, skipfooter=2, engine="python")
    for col in df.filter(regex="(^p|mean)").columns:
        df[col] = df[col] / 1000
    return df


def load_run_data_folder(folder_path: str) -> List[pd.DataFrame]:
    return [
        load_run_data(os.path.join(folder_path, file))
        for file in os.listdir(folder_path)
        if file in ["run_1.txt", "run_2.txt", "run_3.txt"]
    ]


def get_mean_std(df_itr: Iterable[pd.DataFrame], key: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get mean and std of a key from a list of dataframes.

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
    plt.ylabel(ylabel or "95th Percentile Latency [ms]", labelpad=10, fontsize=12)
    plt.title(title or "95th Percentile Latency wrt. QPS", pad=10, fontsize=12)


def plot_errorbar(x, y, xerr, yerr, label, color="black", marker="o"):
    plt.errorbar(x=x, y=y, xerr=xerr, yerr=yerr, fmt=marker, color=color, ecolor=color, elinewidth=2, alpha=0.7)
    plt.plot(x, y, marker, label=label, color=color, alpha=1, markersize=5, linestyle=":")


if __name__ == "__main__":

    while not os.path.exists("scripts"):
        os.chdir("../")

    plt_setup(xlim=(0, 55e3 + 1), ylim=(0, 8))
    colors = cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])
    listdir = [l for l in os.listdir("results/task1") if l.startswith("ibench") or l.startswith("no_interference")]
    benchmarks = [b for b in listdir if os.path.isdir(f"results/task1/{b}")]
    for i, benchmark in enumerate(benchmarks):
        dfs = load_run_data_folder(f"results/task1/{benchmark}")
        p95_mean, p95_std = get_mean_std(dfs, "p95")
        qps_mean, qps_std = get_mean_std(dfs, "QPS")
        plot_errorbar(
            qps_mean,
            p95_mean,
            qps_std,
            p95_std,
            marker=MARKERS[i % len(MARKERS)],
            label=f"{label_mapping[benchmark]}",
            color=next(colors),
        )
    plt.legend(loc="upper right")
    plt.subplots_adjust(left=0.08, right=0.92, bottom=0.08, top=0.95)
    plt.savefig("results/task1/plots/latency_95th_percentile_qps_part1.png")
    plt.show()
