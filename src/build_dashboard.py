"""Build a standalone interactive HTML dashboard (preview of the Tableau dashboard)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import TABLEAU, REPORTS

BLUE, RED, GREEN, GREY = "#2E86C1", "#C0392B", "#27AE60", "#95A5A6"


def styled(fig, height=390, legend=False):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=20, r=20, t=50, b=20),
                      font=dict(family="Segoe UI, Arial", size=12), title_font=dict(size=15), showlegend=legend)
    return fig


def main():
    resp = pd.read_csv(TABLEAU / "responses.csv")
    ratings = pd.read_csv(TABLEAU / "ratings_long.csv")
    priority = pd.read_csv(TABLEAU / "priority_areas.csv")
    gaps = pd.read_csv(TABLEAU / "segment_priority_gaps.csv")
    themes = pd.read_csv(TABLEAU / "theme_summary.csv")
    weekly = pd.read_csv(TABLEAU / "sentiment_trend_weekly.csv")
    quality = pd.read_csv(TABLEAU / "survey_quality_change.csv")
    qwave = pd.read_csv(TABLEAU / "survey_quality_by_wave.csv")

    complete = resp[resp["status"] == "Complete"]
    nps = 100 * ((complete.nps_likelihood >= 9).mean() - (complete.nps_likelihood <= 6).mean())
    commented = resp[resp["sentiment"] != "No Comment"]

    priority["color"] = priority["priority_area"].map({True: "Priority area", False: "Other"})
    ipa = px.scatter(priority, x="mean_score", y="importance_r", size="mentions", color="color", text="label",
                     color_discrete_map={"Priority area": RED, "Other": BLUE},
                     title="Importance-Performance Matrix", labels={"mean_score": "Performance (mean 1 to 5)",
                                                                     "importance_r": "Importance (r with overall)"})
    ipa.update_traces(textposition="top center")
    ipa.add_vline(x=priority["mean_score"].mean(), line_dash="dash", line_color=GREY)
    ipa.add_hline(y=priority["importance_r"].median(), line_dash="dash", line_color=GREY)

    area = ratings.groupby("service_area").agg(mean_score=("score", "mean"), top2box=("top2box", "mean")).reset_index()
    area["top2box_pct"] = (100 * area["top2box"]).round(1)
    scores = px.bar(area.sort_values("top2box_pct"), x="top2box_pct", y="service_area", orientation="h",
                    text="top2box_pct", color_discrete_sequence=[BLUE], title="Top-2-Box Satisfaction by Service Area (%)")

    trend = px.line(weekly, x="week", y="avg_sentiment", color="wave", markers=True,
                    title="Weekly Comment Sentiment Trend (VADER)")
    trend.add_hline(y=0, line_color=GREY)

    th = themes.sort_values("mentions")
    theme_fig = go.Figure([
        go.Bar(y=th["theme_label"], x=(th["mentions"] * th["negative_share"]).round(), name="Negative",
               orientation="h", marker_color=RED),
        go.Bar(y=th["theme_label"], x=(th["mentions"] * th["positive_share"]).round(), name="Positive",
               orientation="h", marker_color=GREEN),
    ])
    theme_fig.update_layout(barmode="stack", title="Key Themes in Comments by Sentiment")

    gaps["segment_group"] = gaps["segment"].str.replace("_", " ").str.title() + ": " + gaps["group"]
    gaps["row"] = gaps["segment_group"] + " | " + gaps["label"]
    gap_fig = px.bar(gaps.sort_values("gap", ascending=False), x="gap", y="row", orientation="h",
                     color_discrete_sequence=[RED], hover_data=["group_mean", "rest_mean", "p_value"],
                     title="Significant Segment Gaps vs Other Respondents (p < 0.05)")

    q = quality.melt(id_vars="metric", value_vars=["wave_1", "wave_2"], var_name="wave", value_name="value")
    q["wave"] = q["wave"].map({"wave_1": "Wave 1 (42 items)", "wave_2": "Wave 2 (24 items)"})
    quality_fig = px.bar(q, x="metric", y="value", color="wave", barmode="group", text="value",
                         color_discrete_map={"Wave 1 (42 items)": GREY, "Wave 2 (24 items)": BLUE},
                         title="Survey Redesign: Response Rate and Data Quality")

    seg = ratings.groupby(["class_standing", "service_area"])["score"].mean().reset_index()
    heat = px.density_heatmap(seg, x="service_area", y="class_standing", z="score", histfunc="avg",
                              color_continuous_scale="RdYlGn", text_auto=".2f",
                              title="Mean Rating by Class Standing and Service Area")

    sent_mix = commented.groupby(["wave", "sentiment"]).size().reset_index(name="comments")
    mix = px.bar(sent_mix, x="wave", y="comments", color="sentiment", text="comments",
                 color_discrete_map={"Positive": GREEN, "Neutral": GREY, "Negative": RED},
                 title="Comment Sentiment Mix by Wave")

    figs = [(ipa, True), (scores, False), (theme_fig, True), (trend, True),
            (gap_fig, False), (heat, False), (quality_fig, True), (mix, True)]
    for f, legend in figs:
        styled(f, 460 if f is gap_fig else 390, legend)

    w2 = qwave.iloc[1]
    kpis = [
        ("Complete Responses", f"{len(complete):,}"),
        ("Comments Analyzed", f"{len(commented):,}"),
        ("Net Promoter Score", f"{nps:.0f}"),
        ("Priority Areas", f"{int(priority['priority_area'].sum())}"),
        ("Response Rate (Wave 2)", f"{w2.response_rate_pct:.1f}%"),
        ("Response Rate Lift", f"+{quality.loc[0, 'change_pts']:.1f} pts"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for l, v in kpis)
    charts = "".join(f'<div class="card">{f.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False)}</div>'
                     for i, (f, _) in enumerate(figs))
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Survey Analytics & Insights Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#F4F6F7;margin:0;color:#1C2833}}
header{{background:#1B4F72;color:#fff;padding:22px 32px}} header h1{{margin:0;font-size:24px}}
header p{{margin:6px 0 0;color:#D6EAF8}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;padding:20px 32px}}
.kpi{{background:#fff;border-left:5px solid {BLUE};padding:14px 16px;border-radius:6px;box-shadow:0 1px 3px #0001}}
.kpi .v{{font-size:26px;font-weight:700}} .kpi .l{{font-size:12px;color:#5D6D7E;text-transform:uppercase}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:16px;padding:0 32px 32px}}
.card{{background:#fff;border-radius:6px;padding:8px;box-shadow:0 1px 3px #0001;overflow-x:auto}}
</style></head><body>
<header><h1>Survey Analytics & Insights Dashboard</h1>
<p>Student Experience Survey, Fall 2025 and Spring 2026: sentiment, themes, segments and priority areas</p></header>
<div class="kpis">{kpi_html}</div><div class="grid">{charts}</div></body></html>"""
    out = REPORTS / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard saved to {out}")


if __name__ == "__main__":
    main()
