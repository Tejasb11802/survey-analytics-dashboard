"""
Demographic segmentation and priority improvement areas.

- Importance-Performance Analysis (IPA): derived importance = correlation of each
  service area with overall satisfaction; performance = mean rating
- Priority score combines importance, performance gap, and negative comment share
- Segment gap analysis: each demographic group vs everyone else (Welch t-test)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from config import RAW, PROCESSED, FIGURES, DIMENSIONS, DIMENSION_LABELS, SEGMENTS

plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})


def importance_performance(c: pd.DataFrame, themes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dim in DIMENSIONS:
        valid = c[[dim, "overall_satisfaction"]].dropna()
        r, _ = stats.pearsonr(valid[dim], valid["overall_satisfaction"])
        rows.append({"dimension": dim, "label": DIMENSION_LABELS[dim], "n": len(valid),
                     "mean_score": valid[dim].mean(), "top2box_pct": 100 * (valid[dim] >= 4).mean(),
                     "importance_r": r})
    ipa = pd.DataFrame(rows).merge(themes[["theme", "mentions", "negative_share"]],
                                   left_on="dimension", right_on="theme", how="left").drop(columns="theme")
    ipa[["mentions", "negative_share"]] = ipa[["mentions", "negative_share"]].fillna(0)
    imp_mid, perf_mid = ipa["importance_r"].median(), ipa["mean_score"].mean()

    def quadrant(r):
        hi_imp, hi_perf = r.importance_r >= imp_mid, r.mean_score >= perf_mid
        if hi_imp and not hi_perf:
            return "Concentrate Here"
        if hi_imp and hi_perf:
            return "Keep Up the Good Work"
        if not hi_imp and not hi_perf:
            return "Low Priority"
        return "Possible Overkill"

    ipa["quadrant"] = ipa.apply(quadrant, axis=1)
    norm = lambda s: (s - s.min()) / (s.max() - s.min())
    ipa["priority_score"] = (0.4 * norm(ipa["importance_r"]) + 0.4 * norm(-ipa["mean_score"])
                             + 0.2 * norm(ipa["negative_share"])).round(3)
    ipa["priority_area"] = (ipa["quadrant"] == "Concentrate Here") | (
        (ipa["mean_score"] < perf_mid) & (ipa["negative_share"] >= 0.5))
    ipa = ipa.sort_values("priority_score", ascending=False).reset_index(drop=True)
    ipa["priority_rank"] = np.arange(1, len(ipa) + 1)
    return ipa.round(4)


def segment_gaps(c: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seg in SEGMENTS:
        for grp in c[seg].dropna().unique():
            in_g, out_g = c[c[seg] == grp], c[c[seg] != grp]
            if len(in_g) < 30:
                continue
            for dim in DIMENSIONS + ["overall_satisfaction"]:
                a, b = in_g[dim].dropna(), out_g[dim].dropna()
                t, p = stats.ttest_ind(a, b, equal_var=False)
                pooled = np.sqrt((a.var() + b.var()) / 2)
                rows.append({"segment": seg, "group": grp, "dimension": dim,
                             "label": DIMENSION_LABELS.get(dim, "Overall Satisfaction"),
                             "group_n": len(a), "group_mean": a.mean(), "rest_mean": b.mean(),
                             "gap": a.mean() - b.mean(), "cohens_d": (a.mean() - b.mean()) / pooled if pooled else 0,
                             "p_value": p})
    gaps = pd.DataFrame(rows)
    gaps["significant"] = gaps["p_value"] < 0.05
    return gaps.round(4)


def plot_ipa(ipa: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 7))
    colors = np.where(ipa["priority_area"], "#C0392B", "#2E86C1")
    ax.scatter(ipa["mean_score"], ipa["importance_r"], s=120 + ipa["mentions"], c=colors, alpha=0.8, edgecolor="k")
    for _, r in ipa.iterrows():
        ax.annotate(r["label"], (r["mean_score"], r["importance_r"]), xytext=(6, 6), textcoords="offset points", fontsize=9)
    ax.axvline(ipa["mean_score"].mean(), ls="--", c="grey")
    ax.axhline(ipa["importance_r"].median(), ls="--", c="grey")
    ax.set_xlabel("Performance (mean rating, 1 to 5)")
    ax.set_ylabel("Derived importance (correlation with overall satisfaction)")
    ax.set_title("Importance-Performance Matrix (red = priority improvement area)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "importance_performance_matrix.png")
    plt.close(fig)


def plot_heatmap(c: pd.DataFrame) -> None:
    blocks = []
    for seg in ["class_standing", "student_type", "residence", "participation_frequency"]:
        m = c.groupby(seg)[DIMENSIONS].mean()
        m.index = [f"{seg.replace('_', ' ').title()}: {i}" for i in m.index]
        blocks.append(m)
    heat = pd.concat(blocks)
    heat.columns = [DIMENSION_LABELS[d] for d in heat.columns]
    fig, ax = plt.subplots(figsize=(13, 7))
    im = ax.imshow(heat.values, cmap="RdYlGn", vmin=2.2, vmax=4.4, aspect="auto")
    ax.set_xticks(range(len(heat.columns)), heat.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(heat.index)), heat.index)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Mean rating")
    ax.set_title("Service Ratings by Demographic Segment", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "segment_heatmap.png")
    plt.close(fig)


def main():
    df = pd.read_csv(RAW / "responses.csv")
    c = df[df["status"] == "Complete"].copy()
    themes = pd.read_csv(PROCESSED / "theme_summary.csv")

    ipa = importance_performance(c, themes)
    ipa.to_csv(PROCESSED / "priority_areas.csv", index=False)
    gaps = segment_gaps(c)
    gaps.to_csv(PROCESSED / "segment_gaps.csv", index=False)
    critical = gaps[(gaps["significant"]) & (gaps["gap"] <= -0.25)
                    & (gaps["dimension"] != "overall_satisfaction")].sort_values("gap")
    critical.to_csv(PROCESSED / "segment_priority_gaps.csv", index=False)

    means = c.melt(id_vars=SEGMENTS, value_vars=DIMENSIONS, var_name="dimension", value_name="score").dropna()
    means["label"] = means["dimension"].map(DIMENSION_LABELS)
    means.to_csv(PROCESSED / "ratings_long.csv", index=False)

    plot_ipa(ipa)
    plot_heatmap(c)

    flagged = ipa[ipa["priority_area"]]
    print(f"Complete responses analyzed: {len(c):,}")
    print(f"\n{len(flagged)} priority improvement areas identified:")
    print(flagged[["priority_rank", "label", "mean_score", "top2box_pct", "importance_r",
                   "negative_share", "quadrant"]].to_string(index=False))
    print(f"\n{len(critical)} statistically significant segment gaps (p < 0.05, gap <= -0.25). Top 8:")
    print(critical.head(8)[["segment", "group", "label", "group_mean", "rest_mean", "gap", "p_value"]].to_string(index=False))


if __name__ == "__main__":
    main()
