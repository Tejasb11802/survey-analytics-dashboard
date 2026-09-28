"""
Survey design optimization: compare Wave 1 (original) vs Wave 2 (redesigned).

Metrics: response rate, completion rate, median completion time, straightlining,
item nonresponse and open-text comment rate.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import RAW, PROCESSED, FIGURES, DIMENSIONS

DESIGN_CHANGES = [
    ("Length", "Cut instrument from 42 to 24 items by removing redundant and low-variance questions"),
    ("Question wording", "Split double-barreled questions (e.g. 'hours and scheduling') into single-concept items"),
    ("Scale consistency", "Standardized every rating item to one 5-point agreement scale with labeled endpoints"),
    ("Flow", "Moved demographics to the end and grouped items by service area"),
    ("Attention check", "Added one instructed-response item to flag straightlining"),
    ("Mobile", "Replaced large matrix grids with single-item mobile-friendly screens"),
    ("Outreach", "Personalized invitation plus two reminders timed to class breaks"),
]


def main():
    df = pd.read_csv(RAW / "responses.csv")
    df["comment"] = df["comment"].fillna("")
    inv = pd.read_csv(RAW / "invitations.csv").set_index("wave")
    rows = []
    for wave, g in df.groupby("wave"):
        c = g[g["status"] == "Complete"]
        rows.append({
            "wave": wave,
            "instrument_items": int(inv.loc[wave, "instrument_items"]),
            "invited": int(inv.loc[wave, "invited"]),
            "survey_starts": len(g),
            "complete_responses": len(c),
            "response_rate_pct": 100 * len(c) / inv.loc[wave, "invited"],
            "completion_rate_pct": 100 * len(c) / len(g),
            "median_minutes": c["duration_minutes"].median(),
            "straightlining_pct": 100 * c["straightliner_flag"].mean(),
            "item_nonresponse_pct": 100 * c[DIMENSIONS].isna().mean().mean(),
            "comment_rate_pct": 100 * (c["comment"].str.len() > 0).mean(),
        })
    q = pd.DataFrame(rows).round(3)
    q.to_csv(PROCESSED / "survey_quality_by_wave.csv", index=False)
    pd.DataFrame(DESIGN_CHANGES, columns=["area", "change"]).to_csv(PROCESSED / "design_changes.csv", index=False)

    w1, w2 = q.iloc[0], q.iloc[1]
    change = pd.DataFrame({
        "metric": ["Response rate (%)", "Completion rate (%)", "Median minutes", "Straightlining (%)",
                   "Item nonresponse (%)", "Comment rate (%)"],
        "wave_1": [w1.response_rate_pct, w1.completion_rate_pct, w1.median_minutes, w1.straightlining_pct,
                   w1.item_nonresponse_pct, w1.comment_rate_pct],
        "wave_2": [w2.response_rate_pct, w2.completion_rate_pct, w2.median_minutes, w2.straightlining_pct,
                   w2.item_nonresponse_pct, w2.comment_rate_pct],
    })
    change["change_pts"] = (change["wave_2"] - change["wave_1"]).round(2)
    change.round(2).to_csv(PROCESSED / "survey_quality_change.csv", index=False)

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(change))
    ax.bar(x - 0.2, change["wave_1"], 0.4, label="Wave 1: original (42 items)", color="#95A5A6")
    ax.bar(x + 0.2, change["wave_2"], 0.4, label="Wave 2: redesigned (24 items)", color="#2E86C1")
    for i, (a, b) in enumerate(zip(change["wave_1"], change["wave_2"])):
        ax.text(i - 0.2, a + 1, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 1, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, change["metric"], rotation=15)
    ax.set_title("Survey Redesign Impact: Response Rate and Data Quality", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "survey_quality_comparison.png")
    plt.close(fig)

    print(change.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
