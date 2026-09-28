"""Write clean, Tableau-ready extracts to the tableau/ folder."""
import shutil
import pandas as pd
from config import RAW, PROCESSED, TABLEAU, DIMENSIONS, DIMENSION_LABELS


def main():
    df = pd.read_csv(RAW / "responses.csv")
    comments = pd.read_csv(PROCESSED / "comments_scored.csv")[["response_id", "compound", "sentiment", "themes"]]
    resp = df.drop(columns=DIMENSIONS).merge(comments, on="response_id", how="left")
    resp["sentiment"] = resp["sentiment"].fillna("No Comment")
    resp.to_csv(TABLEAU / "responses.csv", index=False)

    ratings = df.melt(id_vars=["response_id", "wave", "status", "class_standing", "college", "residence",
                               "student_type", "gender", "participation_frequency"],
                      value_vars=DIMENSIONS, var_name="dimension", value_name="score").dropna(subset=["score"])
    ratings = ratings[ratings["status"] == "Complete"]
    ratings["service_area"] = ratings["dimension"].map(DIMENSION_LABELS)
    ratings["top2box"] = (ratings["score"] >= 4).astype(int)
    ratings.to_csv(TABLEAU / "ratings_long.csv", index=False)

    copies = {
        "priority_areas.csv": "priority_areas.csv",
        "segment_priority_gaps.csv": "segment_priority_gaps.csv",
        "theme_summary.csv": "theme_summary.csv",
        "theme_mentions.csv": "theme_mentions.csv",
        "sentiment_trend_weekly.csv": "sentiment_trend_weekly.csv",
        "survey_quality_by_wave.csv": "survey_quality_by_wave.csv",
        "survey_quality_change.csv": "survey_quality_change.csv",
    }
    for src, name in copies.items():
        shutil.copy(PROCESSED / src, TABLEAU / name)
    print(f"Tableau extracts written to {TABLEAU}")


if __name__ == "__main__":
    main()
