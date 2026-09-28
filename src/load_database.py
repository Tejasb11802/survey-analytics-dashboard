"""Normalize survey data into SQLite and run the SQL analysis queries."""
import re
import sqlite3
import pandas as pd
from config import RAW, DB_PATH, SQL_DIR, PROCESSED, DIMENSIONS

RESPONDENT_COLS = ["response_id", "wave", "submitted_at", "status", "class_standing", "college", "residence",
                   "student_type", "gender", "participation_frequency", "age_group", "overall_satisfaction",
                   "nps_likelihood", "duration_minutes", "straightliner_flag"]


def load() -> None:
    responses = pd.read_csv(RAW / "responses.csv", keep_default_na=True)
    invitations = pd.read_csv(RAW / "invitations.csv")
    ratings = responses.melt(id_vars="response_id", value_vars=DIMENSIONS, var_name="dimension", value_name="score")
    comments = responses.loc[responses["comment"].fillna("").str.len() > 0, ["response_id", "comment"]]
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript((SQL_DIR / "schema.sql").read_text())
        invitations.to_sql("invitations", conn, if_exists="append", index=False)
        responses[RESPONDENT_COLS].to_sql("respondents", conn, if_exists="append", index=False)
        ratings.to_sql("ratings", conn, if_exists="append", index=False)
        comments.to_sql("comments", conn, if_exists="append", index=False)
    print(f"Loaded {len(responses):,} respondents, {ratings.score.notna().sum():,} ratings, "
          f"{len(comments):,} comments into {DB_PATH.name}")


def run_queries() -> dict:
    blocks = re.split(r"--\s*name:\s*", (SQL_DIR / "analysis_queries.sql").read_text())[1:]
    results = {}
    with sqlite3.connect(DB_PATH) as conn:
        for block in blocks:
            name, query = block.split("\n", 1)
            df = pd.read_sql_query(query, conn)
            df.to_csv(PROCESSED / f"sql_{name.strip()}.csv", index=False)
            results[name.strip()] = df
    print(f"Ran {len(results)} SQL queries, outputs saved to data/processed/")
    print(results["response_rate_by_wave"].to_string(index=False))
    return results


def main():
    load()
    run_queries()


if __name__ == "__main__":
    main()
