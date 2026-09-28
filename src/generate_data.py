"""
Generate a realistic synthetic student experience survey (two waves).

Wave 1 (Fall 2025): original 42-item instrument.
Wave 2 (Spring 2026): redesigned 24-item instrument after design review.

Outputs (data/raw/):
    invitations.csv   invited counts per wave
    responses.csv     one row per survey start, with demographics, ratings,
                      NPS, open-text comment and data quality fields
"""
import numpy as np
import pandas as pd
from config import RAW, DIMENSIONS, RANDOM_STATE

WAVES = {
    "Wave 1 - Fall 2025": dict(start="2025-10-06", days=35, invited=2400, starts=640, complete_p=0.74,
                               straightline_p=0.13, item_missing=0.085, median_min=16.5, comment_p=0.62),
    "Wave 2 - Spring 2026": dict(start="2026-02-09", days=35, invited=2400, starts=720, complete_p=0.90,
                                 straightline_p=0.04, item_missing=0.025, median_min=7.5, comment_p=0.74),
}

# Baseline performance by dimension (1 to 5 scale); lower = weaker area
BASE = {
    "facilities_cleanliness": 3.95, "equipment_availability": 3.05, "scheduling_hours": 2.95,
    "staff_support": 4.10, "communication": 3.10, "registration_process": 3.00,
    "cost_value": 3.15, "safety": 4.20, "program_variety": 3.70, "accessibility": 3.35,
}
# Wave 2 adjustments (some fixes landed between waves)
WAVE2_SHIFT = {"communication": 0.20, "registration_process": 0.15, "equipment_availability": -0.05}

# Segment effects: (segment column, group) -> {dimension: shift}
EFFECTS = {
    ("student_type", "International"): {"communication": -0.55, "registration_process": -0.35, "cost_value": -0.30},
    ("class_standing", "Graduate"): {"scheduling_hours": -0.60, "program_variety": -0.35},
    ("class_standing", "Freshman"): {"registration_process": -0.45, "communication": -0.20},
    ("residence", "Off-Campus"): {"scheduling_hours": -0.40, "accessibility": -0.35},
    ("participation_frequency", "Weekly+"): {"equipment_availability": -0.45, "facilities_cleanliness": -0.15},
    ("participation_frequency", "Rarely"): {"program_variety": -0.30, "communication": -0.25},
}
IMPORTANCE = {
    "facilities_cleanliness": 0.08, "equipment_availability": 0.16, "scheduling_hours": 0.17,
    "staff_support": 0.07, "communication": 0.13, "registration_process": 0.12,
    "cost_value": 0.12, "safety": 0.03, "program_variety": 0.06, "accessibility": 0.10,
}

PHRASES = {
    "equipment_availability": {
        "neg": ["There are never enough squat racks during peak hours.", "Equipment is always taken after 4pm and half the machines are broken.",
                "Waiting 20 minutes for a bench is frustrating.", "Too many broken machines that stay out of order for weeks.",
                "Not enough equipment for the number of students using the gym."],
        "pos": ["Equipment is modern and usually available.", "Love the new free weight area, plenty of equipment.",
                "Machines are well maintained and easy to find."],
    },
    "scheduling_hours": {
        "neg": ["Hours are too limited, please open earlier and close later.", "Weekend hours are terrible for students who work.",
                "Classes are scheduled when grad students are in lab, very inconvenient.", "The facility closes way too early on Fridays.",
                "Schedule changes without notice and the hours do not fit my class schedule."],
        "pos": ["Hours work great with my class schedule.", "Extended evening hours are really helpful.",
                "Flexible scheduling makes it easy to fit a workout in."],
    },
    "communication": {
        "neg": ["I never know about events until they are over, communication is poor.", "Emails are confusing and announcements come too late.",
                "Hard to find information about programs, the website is outdated.", "As an international student I did not understand the emails about registration.",
                "Nobody told us the pool was closed, better communication please."],
        "pos": ["The weekly newsletter is clear and helpful.", "Instagram updates keep me informed about events.",
                "Communication from staff has improved a lot."],
    },
    "registration_process": {
        "neg": ["Registration is confusing and the portal crashes.", "Signing up for intramurals took forever and the form kept failing.",
                "Registration fills up in minutes, the process feels unfair.", "The online registration system is not intuitive for new students.",
                "Too many steps to register for a club, very frustrating."],
        "pos": ["Registration was quick and easy.", "The new sign up portal is simple to use.",
                "Registering for classes online was smooth."],
    },
    "cost_value": {
        "neg": ["Fees are too expensive for what we get.", "Club dues are high and not affordable for many students.",
                "The cost of guest passes and classes adds up, not worth the price.", "Paying extra for group fitness feels unfair on top of student fees."],
        "pos": ["Great value for the student fee.", "Affordable programs compared to off campus gyms.",
                "Free classes are an amazing benefit."],
    },
    "accessibility": {
        "neg": ["Parking is a nightmare and the facility is hard to reach from off campus.", "Accessibility for students with disabilities needs work, the ramp is always blocked.",
                "Hard to get to the rec center without a car.", "Locker rooms are not accessible and the elevator is often broken."],
        "pos": ["Easy to get to from my dorm.", "Accessible entrances and helpful accommodations.",
                "The shuttle stop right outside makes access easy."],
    },
    "facilities_cleanliness": {
        "neg": ["Locker rooms are dirty and smell bad.", "Showers need cleaning more often.",
                "Equipment is not wiped down and the facility feels unclean at night."],
        "pos": ["Facilities are clean and well kept.", "The locker rooms are always spotless.",
                "Really impressed with how clean everything is."],
    },
    "staff_support": {
        "neg": ["Front desk staff were rude when I asked for help.", "Staff seem distracted and unhelpful at times."],
        "pos": ["Staff are friendly and always willing to help.", "The trainers are knowledgeable and supportive.",
                "Front desk staff are welcoming and helpful.", "Coaches went out of their way to help me feel included."],
    },
    "safety": {
        "neg": ["The parking lot feels unsafe at night.", "Would like more staff supervision in the weight room for safety."],
        "pos": ["I always feel safe at the facility.", "Great safety protocols and well lit areas.",
                "Staff take safety seriously, very reassuring."],
    },
    "program_variety": {
        "neg": ["Need more variety in group fitness classes.", "Programs are the same every semester, add more options for grad students.",
                "Would love more club sports and outdoor trips, variety is limited."],
        "pos": ["Great variety of classes and clubs.", "Love the range of intramural sports offered.",
                "So many programs to choose from, something for everyone."],
    },
}
OPENERS = ["", "", "", "Overall, ", "Honestly, ", "In general, ", "One thing: ", "Mostly, "]
CLOSERS = ["", "", "", " Thanks!", " Please fix this.", " Keep it up.", " Would appreciate improvements.", " Otherwise it is fine."]


def pick(rng, p):
    keys = list(p)
    return rng.choice(keys, p=np.array(list(p.values())) / sum(p.values()))


def make_comment(rng, row) -> str:
    scores = {d: row[d] for d in DIMENSIONS if not pd.isna(row[d])}
    lows = sorted(scores, key=scores.get)[:3]
    highs = sorted(scores, key=scores.get, reverse=True)[:3]
    parts = []
    n_themes = rng.choice([1, 1, 2, 2, 3])
    for _ in range(n_themes):
        if rng.random() < 0.68:
            dim = rng.choice(lows)
            tone = "neg" if scores[dim] <= 3 or rng.random() < 0.5 else "pos"
        else:
            dim = rng.choice(highs)
            tone = "pos" if scores[dim] >= 3 else "neg"
        parts.append(rng.choice(PHRASES[dim][tone]))
    body = " ".join(dict.fromkeys(parts))
    opener = rng.choice(OPENERS)
    if opener:
        body = body[0].lower() + body[1:]
    text = opener + body + rng.choice(CLOSERS)
    return text.strip()


def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_STATE)
    rows, rid = [], 1
    for wave, cfg in WAVES.items():
        n = cfg["starts"]
        for i in range(n):
            demo = {
                "class_standing": pick(rng, {"Freshman": 0.22, "Sophomore": 0.20, "Junior": 0.20, "Senior": 0.20, "Graduate": 0.18}),
                "college": pick(rng, {"Engineering": 0.22, "Business": 0.18, "Liberal Arts": 0.18, "Sciences": 0.16,
                                      "Health Solutions": 0.14, "Design & Arts": 0.12}),
                "residence": pick(rng, {"On-Campus": 0.42, "Off-Campus": 0.58}),
                "student_type": pick(rng, {"Domestic": 0.80, "International": 0.20}),
                "gender": pick(rng, {"Female": 0.50, "Male": 0.46, "Non-binary / Other": 0.04}),
                "participation_frequency": pick(rng, {"Weekly+": 0.45, "Monthly": 0.35, "Rarely": 0.20}),
            }
            demo["age_group"] = "25+" if demo["class_standing"] == "Graduate" and rng.random() < 0.6 else \
                ("18-20" if demo["class_standing"] in ("Freshman", "Sophomore") else "21-24")
            trait = rng.normal(0, 0.35)
            straightliner = rng.random() < cfg["straightline_p"]
            complete = rng.random() < cfg["complete_p"]
            ratings = {}
            sl_value = int(rng.choice([3, 4, 5], p=[0.3, 0.4, 0.3]))
            for dim in DIMENSIONS:
                mu = BASE[dim] + trait + (WAVE2_SHIFT.get(dim, 0) if "Wave 2" in wave else 0)
                for (col, grp), eff in EFFECTS.items():
                    if demo[col] == grp:
                        mu += eff.get(dim, 0)
                score = sl_value if straightliner else int(np.clip(np.round(rng.normal(mu, 0.85)), 1, 5))
                ratings[dim] = score
            answered_share = 1.0 if complete else rng.uniform(0.2, 0.7)
            for j, dim in enumerate(DIMENSIONS):
                if (j / len(DIMENSIONS)) >= answered_share or rng.random() < cfg["item_missing"]:
                    ratings[dim] = np.nan
            vals = np.array([ratings[d] for d in DIMENSIONS], dtype=float)
            w = np.array([IMPORTANCE[d] for d in DIMENSIONS])
            mask = ~np.isnan(vals)
            weighted = (vals[mask] * w[mask]).sum() / w[mask].sum() if mask.any() else 3
            overall = int(np.clip(np.round(2.35 * weighted - 0.1 + rng.normal(0, 0.7)), 1, 10)) if complete else np.nan
            nps = int(np.clip(np.round(overall + rng.normal(0, 1.0)), 0, 10)) if complete else np.nan
            ts = pd.Timestamp(cfg["start"]) + pd.Timedelta(days=float(rng.beta(1.3, 2.6) * cfg["days"])) \
                + pd.Timedelta(hours=float(rng.uniform(7, 23)))
            duration = float(np.round(rng.lognormal(np.log(cfg["median_min"]), 0.45), 1))
            if straightliner:
                duration = round(duration * 0.35, 1)
            if not complete:
                duration = round(duration * answered_share, 1)
            row = {"response_id": f"R{rid:05d}", "wave": wave, "submitted_at": ts.strftime("%Y-%m-%d %H:%M"),
                   "status": "Complete" if complete else "Partial", **demo, **ratings,
                   "overall_satisfaction": overall, "nps_likelihood": nps,
                   "duration_minutes": duration, "straightliner_flag": int(straightliner)}
            row["comment"] = make_comment(rng, row) if complete and rng.random() < cfg["comment_p"] else ""
            rows.append(row)
            rid += 1
    responses = pd.DataFrame(rows)
    invitations = pd.DataFrame([{"wave": w, "invited": c["invited"],
                                 "instrument_items": 42 if "Wave 1" in w else 24} for w, c in WAVES.items()])
    return responses, invitations


def main():
    responses, invitations = generate()
    responses.to_csv(RAW / "responses.csv", index=False)
    invitations.to_csv(RAW / "invitations.csv", index=False)
    complete = (responses.status == "Complete").sum()
    print(f"Generated {len(responses):,} survey starts, {complete:,} complete responses")
    print(f"Comments: {(responses.comment != '').sum():,}")


if __name__ == "__main__":
    main()
