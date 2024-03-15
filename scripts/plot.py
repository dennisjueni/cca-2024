import sys
import pandas as pd
import re, os
from typing import Iterable, List, Tuple
import numpy as np
from pandas import DataFrame
import matplotlib.pyplot as plt
import seaborn as sns


def load_run_data(file_path: str) -> pd.DataFrame:
    with open(file_path, "r") as f:
        lines = [line for line in f.readlines() if re.match(r"^(\#type|read)", line)]
        keys = lines[0].split()[1:]
        data = {k: [] for k in keys}
        for line in lines[1:]:
            line_values = line.split()[1:]
            for i, key in enumerate(keys):
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


def plot_errorbar(x, y, xerr, yerr, xlim, ylim, title=None, xlabel=None, ylabel=None, save_path=None, colored=False):
    sns.set_palette("deep")
    sns.set_style("whitegrid")
    plt.figure(figsize=(8, 4), dpi=150)
    plt.rcParams["font.size"] = 12
    plt.rcParams["font.family"] = "Arial"
    plt.grid(linestyle="--", linewidth=0.5, color="gray", which="both", alpha=0.5)
    sns.despine(left=True, bottom=True)
    plt.xlim(xlim)
    plt.ylim(ylim)
    # set figure size
    plt.xlabel(xlabel or "QPS [queries/s]", labelpad=10, fontsize=12)  # Adjust labelpad and fontsize
    plt.ylabel(ylabel or "Latency [ms] 95th Percentile", labelpad=10, fontsize=12)
    plt.title(title or "Latency 95th Percentile wrt. QPS", pad=10, fontsize=12)
    # generate color based on index
    if colored:
        colors = [[1 - 1 * i / len(x) for _ in range(3)] for i in range(len(x))]
        for i in range(len(x)):
            plt.errorbar(
                x=x[i],
                y=y[i],
                xerr=xerr[i],
                yerr=yerr[i],
                fmt="o",
                color=colors[i],
                ecolor="lightgray",
                elinewidth=3,
                capsize=0,
                alpha=0.6,
            )
    else:
        plt.errorbar(
            x=x,
            y=y,
            xerr=xerr,
            yerr=yerr,
            fmt="o",
            color="black",
            ecolor="lightgray",
            elinewidth=3,
            capsize=0,
            alpha=0.6,
        )
    plt.plot(x, y, "o:", color="black", alpha=0.8, markersize=5)
    plt.subplots_adjust(bottom=0.15)
    if save_path:
        plt.savefig(save_path)
    plt.show()
    plt.close()


if __name__ == "__main__":
    while not os.path.exists("scripts"):
        os.chdir("../")

    # check if --task1 flag is present
    if "--task1" in sys.argv:
        benchmarks = os.listdir("results")
        for benchmark in benchmarks:
            dfs = load_run_data_folder(f"results/{benchmark}")
            p95_mean, p95_std = get_mean_std(dfs, "p95")
            qps_mean, qps_std = get_mean_std(dfs, "QPS")
            plot_errorbar(
                qps_mean,
                p95_mean,
                qps_std,
                p95_std,
                title=f"{benchmark} : Latency 95th / QPS",
                xlim=(0, 55e3),
                ylim=(0, 8e3),
                colored=True,
                save_path=f"results/{benchmark}/plot_p95_qps.png",
            )
    else:
        print("Please provide a valid flag")
        sys.exit(1)
