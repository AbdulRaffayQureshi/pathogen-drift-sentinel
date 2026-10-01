#!/usr/bin/env python3
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

SVG_PATH = Path(__file__).resolve().parent.parent / "assets" / "telemetry_dashboard.svg"

def render_dashboard(df: pd.DataFrame):
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=120)
    fig.patch.set_facecolor("#0d1117")

    latest_ts = df["timestamp"].max()
    latest_df = df[df["timestamp"] == latest_ts]

    # Panel 1: Bar chart of log10 Indexed Sequences + Delta
    ax1.set_facecolor("#161b22")
    bars = ax1.barh(latest_df["target"], latest_df["count"], color="#238636", edgecolor="#2ea043")
    ax1.set_xscale("log")
    ax1.set_title("NCBI Indexed Sequences (Log Scale)", fontsize=11, color="#c9d1d9", pad=10)
    ax1.set_xlabel("Total Nucleotide Records", color="#8b949e")
    ax1.grid(axis="x", linestyle="--", alpha=0.25)

    # Panel 2: Scatter of GC% vs 3-mer Shannon Complexity colored by Anomaly Score
    ax2.set_facecolor("#161b22")
    colors = ["#f85149" if flag == "ANOMALY" else "#58a6ff" for flag in latest_df["anomaly_flag"]]
    ax2.scatter(latest_df["gc_pct"], latest_df["kmer_entropy"], c=colors, s=130, edgecolors="white", zorder=4)
    for _, row in latest_df.iterrows():
        ax2.annotate(
            row["target"],
            (row["gc_pct"], row["kmer_entropy"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8.5,
            color="#c9d1d9"
        )
    ax2.set_title("FASTA Sequence Drift: GC% vs 3-mer Entropy", fontsize=11, color="#c9d1d9", pad=10)
    ax2.set_xlabel("GC Content (%)", color="#8b949e")
    ax2.set_ylabel("3-mer Shannon Complexity (bits)", color="#8b949e")
    ax2.grid(True, linestyle="--", alpha=0.25)

    plt.tight_layout()
    plt.savefig(SVG_PATH, format="svg", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
