"""Shared paths and settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "survey.db"
SQL_DIR = ROOT / "sql"
FIGURES = ROOT / "reports" / "figures"
REPORTS = ROOT / "reports"
TABLEAU = ROOT / "tableau"

RANDOM_STATE = 42

DIMENSIONS = [
    "facilities_cleanliness", "equipment_availability", "scheduling_hours", "staff_support",
    "communication", "registration_process", "cost_value", "safety", "program_variety", "accessibility",
]
DIMENSION_LABELS = {
    "facilities_cleanliness": "Facilities & Cleanliness",
    "equipment_availability": "Equipment Availability",
    "scheduling_hours": "Scheduling & Hours",
    "staff_support": "Staff Support",
    "communication": "Communication",
    "registration_process": "Registration Process",
    "cost_value": "Cost & Value",
    "safety": "Safety",
    "program_variety": "Program Variety",
    "accessibility": "Accessibility",
}
SEGMENTS = ["class_standing", "college", "residence", "student_type", "gender", "participation_frequency"]

for folder in (RAW, PROCESSED, FIGURES, TABLEAU):
    folder.mkdir(parents=True, exist_ok=True)
