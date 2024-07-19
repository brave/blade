import math
import os
import sys

import matplotlib
import matplotlib.pyplot as plt
# import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")


def plot_measurements(df, metric, stages, labels, title, filepath):

    # filter data (and copy)
    df = df[df["stage"].isin(stages)].copy()

    # rename stages with labels
    if labels is not None:
        df.replace({"stage": dict(zip(stages, labels))}, inplace=True)

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(4, 3))

    # plot
    sns.barplot(data=df, x="stage", y=metric, order=labels, ax=ax)
    ax.set_xlabel("")

    # auto ylim
    low = min(df[metric]) - 0.5
    high = max(df[metric]) + 0.5
    ax.set_ylim(low, high)

    fig.suptitle(title)

    plt.tight_layout()
    fig.savefig(filepath, dpi=300)
    plt.close()
