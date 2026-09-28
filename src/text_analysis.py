"""
Open-text analysis of survey comments.

- Sentiment: VADER compound score per comment, labeled Positive / Neutral / Negative
- Theme discovery: TF-IDF + NMF topic model (unsupervised)
- Theme tagging: keyword lexicon mapping each comment to service-area themes
- Sentiment trend: weekly average sentiment across both survey waves
"""
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import RAW, PROCESSED, FIGURES, RANDOM_STATE, DIMENSION_LABELS

plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})

THEME_KEYWORDS = {
    "equipment_availability": ["equipment", "machine", "rack", "bench", "weights", "broken"],
    "scheduling_hours": ["hours", "schedule", "scheduled", "open earlier", "close", "closes", "weekend", "evening"],
    "communication": ["communication", "email", "announce", "newsletter", "website", "information", "instagram", "told"],
    "registration_process": ["registration", "register", "sign up", "portal", "form", "signing up"],
    "cost_value": ["fee", "fees", "cost", "price", "expensive", "affordable", "dues", "paying", "free classes", "value"],
    "accessibility": ["parking", "accessib", "ramp", "elevator", "shuttle", "reach", "get to"],
    "facilities_cleanliness": ["clean", "dirty", "smell", "shower", "spotless", "locker room", "wiped"],
    "staff_support": ["staff", "trainer", "front desk", "coach", "rude"],
    "safety": ["safe", "safety", "well lit", "supervision"],
    "program_variety": ["variety", "clubs", "club sports", "intramural", "programs", "options", "trips"],
}


# Domain lexicon additions so VADER reads campus service feedback correctly
DOMAIN_LEXICON = {
    "broken": -1.8, "limited": -1.3, "crashes": -1.8, "outdated": -1.2, "expensive": -1.4, "blocked": -1.2,
    "inconvenient": -1.6, "late": -0.9, "taken": -0.8, "waiting": -0.9, "forever": -1.0, "early": -0.4,
    "confusing": -1.6, "unclean": -1.8, "overcrowded": -1.6, "spotless": 2.0, "affordable": 1.5,
    "accessible": 1.3, "flexible": 1.2, "smooth": 1.4, "informed": 1.0, "modern": 1.0,
    "enough": 1.0, "intuitive": 1.3, "understand": 1.0, "please": 0.0, "nobody": -1.0, "available": 0.8,
}


def make_analyzer() -> SentimentIntensityAnalyzer:
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(DOMAIN_LEXICON)
    return analyzer


def label_sentiment(c: float) -> str:
    if c >= 0.05:
        return "Positive"
    if c <= -0.05:
        return "Negative"
    return "Neutral"


THEME_PATTERNS = {theme: re.compile(r"\b(" + "|".join(re.escape(k) for k in kws) + ")", re.IGNORECASE)
                  for theme, kws in THEME_KEYWORDS.items()}


def tag_themes(text: str) -> list:
    return [theme for theme, pattern in THEME_PATTERNS.items() if pattern.search(text)]


def sentence_level(comments: pd.DataFrame, analyzer) -> pd.DataFrame:
    """Split comments into sentences so each theme gets the sentiment of its own sentence."""
    rows = []
    for _, r in comments.iterrows():
        for sent in re.split(r"(?<=[.!?])\s+", r["comment"]):
            themes = tag_themes(sent)
            if not themes:
                continue
            score = analyzer.polarity_scores(sent)["compound"]
            for theme in themes:
                rows.append({"response_id": r["response_id"], "wave": r["wave"], "theme": theme,
                             "sentence": sent, "sentence_compound": score, "sentence_sentiment": label_sentiment(score)})
    return pd.DataFrame(rows)


def topic_model(texts: pd.Series, k: int = 8) -> pd.DataFrame:
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=5, max_df=0.5)
    X = vec.fit_transform(texts)
    nmf = NMF(n_components=k, random_state=RANDOM_STATE, init="nndsvda", max_iter=2000).fit(X)
    terms = np.array(vec.get_feature_names_out())
    weights = nmf.transform(X)
    rows = []
    for i, comp in enumerate(nmf.components_):
        top = terms[comp.argsort()[::-1][:8]]
        rows.append({"topic_id": i + 1, "top_terms": ", ".join(top),
                     "comments_dominant": int((weights.argmax(axis=1) == i).sum())})
    return pd.DataFrame(rows).sort_values("comments_dominant", ascending=False)


def main():
    df = pd.read_csv(RAW / "responses.csv")
    df["comment"] = df["comment"].fillna("")
    comments = df[df["comment"].str.len() > 0].copy()
    analyzer = make_analyzer()

    comments["compound"] = comments["comment"].apply(lambda t: analyzer.polarity_scores(t)["compound"])
    comments["sentiment"] = comments["compound"].apply(label_sentiment)
    comments["themes"] = comments["comment"].apply(lambda t: "; ".join(DIMENSION_LABELS[x] for x in tag_themes(t)))
    comments["submitted_at"] = pd.to_datetime(comments["submitted_at"])
    comments["week"] = comments["submitted_at"].dt.to_period("W").dt.start_time.dt.date
    keep = ["response_id", "wave", "submitted_at", "week", "class_standing", "college", "residence", "student_type",
            "participation_frequency", "overall_satisfaction", "comment", "compound", "sentiment", "themes"]
    comments[keep].to_csv(PROCESSED / "comments_scored.csv", index=False)

    sent = sentence_level(comments, analyzer)
    sent.to_csv(PROCESSED / "theme_mentions.csv", index=False)
    theme_summary = (sent.groupby("theme")
                     .agg(mentions=("response_id", "count"),
                          avg_sentiment=("sentence_compound", "mean"),
                          negative_share=("sentence_sentiment", lambda s: (s == "Negative").mean()),
                          positive_share=("sentence_sentiment", lambda s: (s == "Positive").mean()))
                     .reset_index())
    theme_summary["theme_label"] = theme_summary["theme"].map(DIMENSION_LABELS)
    theme_summary = theme_summary.round(4).sort_values("mentions", ascending=False)
    theme_summary.to_csv(PROCESSED / "theme_summary.csv", index=False)

    theme_wave = (sent.groupby(["wave", "theme"]).agg(mentions=("response_id", "count"),
                  negative_share=("sentence_sentiment", lambda s: (s == "Negative").mean())).reset_index())
    theme_wave["theme_label"] = theme_wave["theme"].map(DIMENSION_LABELS)
    theme_wave.round(4).to_csv(PROCESSED / "theme_by_wave.csv", index=False)

    weekly = (comments.groupby(["wave", "week"])
              .agg(comments=("response_id", "count"), avg_sentiment=("compound", "mean"),
                   positive_pct=("sentiment", lambda s: 100 * (s == "Positive").mean()),
                   negative_pct=("sentiment", lambda s: 100 * (s == "Negative").mean()))
              .reset_index().round(3))
    weekly.to_csv(PROCESSED / "sentiment_trend_weekly.csv", index=False)

    topics = topic_model(comments["comment"])
    topics.to_csv(PROCESSED / "nmf_topics.csv", index=False)

    # Figures
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for wave, g in weekly.groupby("wave"):
        ax.plot(pd.to_datetime(g["week"]), g["avg_sentiment"], marker="o", lw=2, label=wave)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_title("Weekly Average Comment Sentiment (VADER compound)", fontweight="bold")
    ax.set_ylabel("Avg sentiment")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "sentiment_trend.png")
    plt.close(fig)

    ts = theme_summary.sort_values("mentions")
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.barh(ts["theme_label"], ts["negative_share"] * ts["mentions"], color="#C0392B", label="Negative")
    ax.barh(ts["theme_label"], ts["positive_share"] * ts["mentions"],
            left=ts["negative_share"] * ts["mentions"], color="#27AE60", label="Positive")
    ax.set_xlabel("Theme mentions")
    ax.set_title("Key Themes in Open-Text Comments by Sentiment", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "theme_sentiment.png")
    plt.close(fig)

    print(f"Scored {len(comments):,} comments: {comments.sentiment.value_counts().to_dict()}")
    print("Top themes:")
    print(theme_summary[["theme_label", "mentions", "avg_sentiment", "negative_share"]].to_string(index=False))
    print("\nNMF discovered topics:")
    print(topics.to_string(index=False))


if __name__ == "__main__":
    main()
