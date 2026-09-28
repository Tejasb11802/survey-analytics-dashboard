# Tableau Dashboard Build Guide

Build the **Survey Analytics & Insights Dashboard** in Tableau Public (free) or Tableau Desktop using the CSV extracts in this folder.

## 1. Connect the Data

1. **Connect > Text file** and select `responses.csv`.
2. Add these as separate data sources (Data > New Data Source): `ratings_long.csv`, `priority_areas.csv`, `segment_priority_gaps.csv`, `theme_summary.csv`, `sentiment_trend_weekly.csv`, `survey_quality_change.csv`.

## 2. Calculated Fields

**responses.csv**

| Name | Formula |
|---|---|
| Complete Responses | `COUNTD(IF [Status] = "Complete" THEN [Response Id] END)` |
| Promoter | `IF [Nps Likelihood] >= 9 THEN 1 ELSE 0 END` |
| Detractor | `IF [Nps Likelihood] <= 6 THEN 1 ELSE 0 END` |
| NPS | `(SUM([Promoter]) - SUM([Detractor])) / COUNT([Nps Likelihood]) * 100` |

**ratings_long.csv**

| Name | Formula |
|---|---|
| Top 2 Box % | `AVG([Top2box])` (format as percentage) |
| Mean Score | `AVG([Score])` |

**priority_areas.csv**

| Name | Formula |
|---|---|
| Priority Flag | `IF [Priority Area] THEN "Priority" ELSE "Other" END` |

## 3. Worksheets

1. **KPI Cards**: Complete Responses, comments (`COUNT` of rows where Sentiment is not "No Comment"), NPS, number of priority areas, Wave 2 response rate.
2. **Importance-Performance Matrix** (`priority_areas`): Columns = Mean Score, Rows = Importance R, Size = Mentions, Color = Priority Flag, Label = Label. Add reference lines: average on Mean Score, median on Importance R.
3. **Top-2-Box by Service Area** (`ratings_long`): Rows = Service Area, Columns = Top 2 Box %, sorted ascending.
4. **Themes by Sentiment** (`theme_summary`): Rows = Theme Label, Columns = Mentions, Color = Negative Share (red-green diverging, reversed).
5. **Sentiment Trend** (`sentiment_trend_weekly`): Columns = Week (continuous), Rows = Avg Sentiment, Color = Wave.
6. **Segment Heatmap** (`ratings_long`): Rows = Class Standing, Columns = Service Area, Color = Mean Score (red-green), Label = Mean Score.
7. **Segment Gaps** (`segment_priority_gaps`): Rows = Group and Label, Columns = Gap, Tooltip = Group Mean, Rest Mean, P Value.
8. **Survey Redesign** (`survey_quality_change`): pivot Wave 1 and Wave 2 (select both columns > right click > Pivot), Columns = Metric, Rows = value, Color = wave.

## 4. Filters

On the ratings and responses sheets: Wave, Class Standing, Student Type, Residence, College, Participation Frequency. Apply to all worksheets using the same data source.

## 5. Dashboard Layout (1400 x 900)

```
+-------------------------------------------------------------------+
| Title | KPI: Responses | KPI: Comments | KPI: NPS | KPI: Priorities |
+----------------------------------+--------------------------------+
| Importance-Performance Matrix    | Themes by Sentiment            |
+----------------------------------+--------------------------------+
| Segment Heatmap                  | Segment Gaps                   |
+----------------------------------+--------------------------------+
| Sentiment Trend                  | Survey Redesign Impact         |
+-------------------------------------------------------------------+
```

Add a Highlight action on Service Area so selecting an area in the matrix highlights it across the heatmap and top-2-box chart.

## 6. Publish

**File > Save to Tableau Public**, then copy the public link into the main README under a "Live Tableau Dashboard" heading.
