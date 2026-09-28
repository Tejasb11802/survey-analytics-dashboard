"""Run the full Survey Analytics & Insights pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import generate_data, load_database, text_analysis, segmentation, survey_quality, export_tableau, build_dashboard  # noqa: E402

STEPS = [
    ("1/7 Generating survey data", generate_data.main),
    ("2/7 Loading SQLite database and running SQL analysis", load_database.main),
    ("3/7 Text analysis: sentiment and themes", text_analysis.main),
    ("4/7 Demographic segmentation and priority areas", segmentation.main),
    ("5/7 Survey design and data quality comparison", survey_quality.main),
    ("6/7 Exporting Tableau extracts", export_tableau.main),
    ("7/7 Building HTML dashboard", build_dashboard.main),
]

if __name__ == "__main__":
    skip_generate = "--skip-generate" in sys.argv  # use when running on your own data
    for title, step in STEPS:
        if skip_generate and step is generate_data.main:
            print(f"Skipping: {title}")
            continue
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
        step()
    print("\nPipeline complete. Open reports/dashboard.html in your browser.")
