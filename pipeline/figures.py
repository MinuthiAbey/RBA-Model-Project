# Draws the result figures (300 dpi PNG) from the evaluation tables.

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from pipeline.common import FIGURES, SCORERS, TABLES

# One fixed colour and marker per scorer in every figure; markers keep series apart without colour.
STYLE = {
    "rforest": {"color": "#2a78d6", "marker": "o", "linestyle": "-", "label": "Random Forest"},
    "freeman": {"color": "#eb6834", "marker": "s", "linestyle": "--", "label": "Freeman (statistical)"},
    "iforest": {"color": "#1baf7a", "marker": "^", "linestyle": "-.", "label": "Isolation Forest"},
    "rules": {"color": "#eda100", "marker": "D", "linestyle": ":", "label": "Rule-based"},
}
ORDER = ["rforest", "freeman", "iforest", "rules"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
ATTACK_PANELS = {"real_attack_ip": ("attack_ip", "Real attacker-IP attempts"),
                 "simulated": ("simulated", "Simulated attacks")}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "axes.axisbelow": True, "lines.linewidth": 2, "legend.frameon": False, "savefig.dpi": 300,
})


def save(fig, name: str) -> None:
    fig.tight_layout(rect=(0, 0.06, 1, 1) if fig.legends else None)
    fig.savefig(FIGURES / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {name}")


def shared_legend(fig, axes) -> None:
    # One legend under the panels, so it never sits on top of a curve.
    handles, labels = axes.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(bottom=0.2)


def percent_axis(axis) -> None:
    axis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))


def roc_figures(scores: pd.DataFrame) -> None:
    legit = scores["kind"] == "legit"
    roc, tradeoff = plt.subplots(1, 2, figsize=(9, 4)), plt.subplots(1, 2, figsize=(9, 4))
    for col, (kind, title) in enumerate(ATTACK_PANELS.values()):
        both = legit | (scores["kind"] == kind)
        labels = (scores.loc[both, "kind"] == kind).to_numpy(int)
        for name in ORDER:
            raw = scores.loc[both, f"{name}_raw"].to_numpy()
            fpr, tpr, _ = roc_curve(labels, raw)
            style = STYLE[name]
            line = dict(color=style["color"], linestyle=style["linestyle"])
            roc[1][col].plot(fpr, tpr, **line, label=f"{style['label']} (AUC {roc_auc_score(labels, raw):.3f})")
            keep = fpr <= 0.30
            tradeoff[1][col].plot(fpr[keep], tpr[keep], **line, label=style["label"])
        roc[1][col].plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle=(0, (2, 2)), label="Random guess")
        tradeoff[1][col].axvline(0.05, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
        tradeoff[1][col].text(0.054, 0.96, "5% budget", color=MUTED, fontsize=8, va="top")
        for axes, xlabel in ((roc[1][col], "False positive rate (legitimate logins flagged)"),
                             (tradeoff[1][col], "Legitimate logins challenged")):
            axes.set_title(title)
            axes.set_xlabel(xlabel)
        roc[1][col].legend(loc="lower right", fontsize=7)  # AUC differs per panel, so each keeps its own
        roc[1][col].set_ylabel("True positive rate (attacks flagged)")
        tradeoff[1][col].set_ylabel("Attacks stopped (OTP or block)")
        percent_axis(tradeoff[1][col].xaxis)
        percent_axis(tradeoff[1][col].yaxis)
        tradeoff[1][col].set_xlim(0, 0.30)
        tradeoff[1][col].set_ylim(0, 1)
    shared_legend(tradeoff[0], tradeoff[1][0])
    save(roc[0], "roc_curves.png")
    save(tradeoff[0], "security_usability_tradeoff.png")


def bucket_lines(axes, table: pd.DataFrame, buckets: list[str], ylabel: str) -> None:
    x = np.arange(len(buckets))
    for name in ORDER:
        rows = table[table["scorer"] == name].set_index("bucket").loc[buckets]
        style = STYLE[name]
        axes.plot(x, rows["rate"], color=style["color"], marker=style["marker"], markersize=6,
                  linestyle=style["linestyle"], label=style["label"])
        axes.fill_between(x, rows["ci_low"], rows["ci_high"], color=style["color"], alpha=0.12, linewidth=0)
    axes.set_xticks(x, buckets)
    axes.set_xlabel("Previous successful logins by this user")
    axes.set_ylabel(ylabel)
    percent_axis(axes.yaxis)


def overlapping_lines(cold: pd.DataFrame, a: str, b: str) -> bool:
    rates = cold.pivot_table(index=["population", "bucket"], columns="scorer", values="rate")
    return bool(np.allclose(rates[a], rates[b], atol=0.005))


def cold_start_figures(cold: pd.DataFrame, buckets: list[str]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for col, (population, (_, title)) in enumerate(ATTACK_PANELS.items()):
        bucket_lines(axes[col], cold[cold["population"] == population], buckets, "Attacks stopped at a 5% challenge budget")
        axes[col].set_title(title)
        axes[col].set_ylim(0, 1)
    if overlapping_lines(cold, "rules", "freeman"):
        axes[0].annotate("Rule-based and Freeman nearly identical", xy=(1, 0.005), xytext=(1.9, 0.045),
                         fontsize=7.5, color=MUTED, arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8})
    shared_legend(fig, axes[0])
    save(fig, "cold_start_curves.png")

    fig, axes = plt.subplots(figsize=(5.5, 4))
    bucket_lines(axes, cold[cold["population"] == "legit"], buckets, "Legitimate logins challenged")
    axes.axhline(0.05, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
    axes.set_title("False challenges by login history")
    axes.set_ylim(0, None)
    axes.legend(loc="upper right", fontsize=8)
    axes.text(2.5, 0.045, "5% budget", color=MUTED, fontsize=8, ha="center", va="top")
    save(fig, "cold_start_false_challenges.png")


def grouped_bars(axes, table: pd.DataFrame, column: str, groups: list[str], labels: list[str]) -> None:
    width = 0.2
    x = np.arange(len(groups))
    for i, name in enumerate(ORDER):
        rows = table[table["scorer"] == name].set_index(column).loc[groups]
        rate = rows["attack_stop_rate"].to_numpy()
        err = np.clip(np.vstack([rate - rows["ci_low"].to_numpy(), rows["ci_high"].to_numpy() - rate]), 0, None)
        axes.bar(x + (i - 1.5) * width, rate, width, color=STYLE[name]["color"], edgecolor="white", linewidth=1,
                 yerr=err, error_kw={"elinewidth": 0.8, "ecolor": MUTED, "capsize": 0}, label=STYLE[name]["label"])
    axes.set_xticks(x, labels)
    axes.set_ylabel("Attacks stopped at a 5% challenge budget")
    axes.set_ylim(0, 1)
    percent_axis(axes.yaxis)


def attacker_type_figure() -> None:
    simulated = pd.read_csv(TABLES / "by_attacker_type.csv")
    real = pd.read_csv(TABLES / "by_attack_context.csv")
    contexts = ["victim_has_no_history", "new_country", "home_country_new_device", "home_country_known_device"]
    contexts = [c for c in contexts if c in set(real["context"])]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    grouped_bars(axes[0], simulated, "attacker_type", ["naive", "vpn", "targeted"], ["Naive", "VPN", "Targeted"])
    axes[0].set_title("Simulated attacks by attacker type")
    grouped_bars(axes[1], real, "context", contexts,
                 [c.replace("victim_has_no_history", "victim has\nno history").replace("home_country_", "home country,\n")
                  .replace("_", " ") for c in contexts])
    axes[1].set_title("Real attacker-IP attempts by match with the victim")
    shared_legend(fig, axes[0])
    save(fig, "attacker_types.png")


def latency_figure() -> None:
    latency = pd.read_csv(TABLES / "latency.csv").set_index("scorer").loc[ORDER]
    fig, axes = plt.subplots(figsize=(6, 3.8))
    x = np.arange(len(ORDER))
    colors = [STYLE[n]["color"] for n in ORDER]
    axes.bar(x - 0.18, latency["p50_us"] / 1000, 0.34, color=colors, edgecolor="white", label="Median (p50)")
    axes.bar(x + 0.18, latency["p95_us"] / 1000, 0.34, color=colors, edgecolor="white", hatch="///", alpha=0.6,
             label="95th percentile (p95)")
    for xi, (p50, p95) in enumerate(zip(latency["p50_us"], latency["p95_us"])):
        axes.text(xi - 0.18, p50 / 1000, readable_time(p50), ha="center", va="bottom", fontsize=7, color=INK)
        axes.text(xi + 0.18, p95 / 1000, readable_time(p95), ha="center", va="bottom", fontsize=7, color=INK)
    axes.set_yscale("log")
    axes.set_xticks(x, [STYLE[n]["label"] for n in ORDER], fontsize=8)
    axes.set_ylabel("Time to score one login (ms, log scale)")
    axes.set_title("Scoring latency per login (features + score + reasons)")
    axes.set_ylim(top=latency["p95_us"].max() / 1000 * 4)
    axes.legend(fontsize=8, loc="upper center")
    save(fig, "latency.png")


def readable_time(microseconds: float) -> str:
    return f"{microseconds:.0f} µs" if microseconds < 1000 else f"{microseconds / 1000:.1f} ms"


def confusion_figure(scores: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(13, 2.7))
    classes = [("legit", "Legitimate"), ("attack_ip", "Real attack")]
    for axis, name in zip(axes, ORDER):
        matrix = np.zeros((2, 3))
        for row, (kind, _) in enumerate(classes):
            rows = scores[scores["kind"] == kind]
            challenge, block = rows[f"{name}_challenge"], rows[f"{name}_block"]
            matrix[row] = [(1 - challenge).sum(), (challenge - block).sum(), block.sum()]
        shares = matrix / matrix.sum(axis=1, keepdims=True)
        axis.imshow(shares, cmap="Blues", vmin=0, vmax=1)
        for (r, c), share in np.ndenumerate(shares):
            axis.text(c, r, f"{share:.1%}\n({matrix[r, c]:,.0f})", ha="center", va="center", fontsize=7.5,
                      color="white" if share > 0.6 else INK)
        axis.set_xticks(range(3), ["Allow", "OTP", "Block"])
        axis.set_yticks(range(2), [label for _, label in classes])
        axis.set_title(STYLE[name]["label"])
        axis.grid(False)
    fig.suptitle("Decisions on the test period (row shares, expected counts)", fontsize=10)
    save(fig, "confusion_matrices.png")


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    scores = pd.read_parquet(TABLES / "test_scores.parquet")
    cold = pd.read_csv(TABLES / "cold_start.csv")
    buckets = list(dict.fromkeys(cold["bucket"]))
    print("Writing figures:")
    roc_figures(scores)
    cold_start_figures(cold, buckets)
    attacker_type_figure()
    latency_figure()
    confusion_figure(scores)
    return 0


if __name__ == "__main__":
    sys.exit(main())
