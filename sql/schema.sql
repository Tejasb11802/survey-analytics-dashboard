-- Survey Analytics & Insights: SQLite schema (normalized)
DROP TABLE IF EXISTS invitations;
DROP TABLE IF EXISTS respondents;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS comments;

CREATE TABLE invitations (
    wave              TEXT PRIMARY KEY,
    invited           INTEGER,
    instrument_items  INTEGER
);

CREATE TABLE respondents (
    response_id              TEXT PRIMARY KEY,
    wave                     TEXT REFERENCES invitations(wave),
    submitted_at             TEXT,
    status                   TEXT,
    class_standing           TEXT,
    college                  TEXT,
    residence                TEXT,
    student_type             TEXT,
    gender                   TEXT,
    participation_frequency  TEXT,
    age_group                TEXT,
    overall_satisfaction     INTEGER,
    nps_likelihood           INTEGER,
    duration_minutes         REAL,
    straightliner_flag       INTEGER
);

CREATE TABLE ratings (
    response_id  TEXT REFERENCES respondents(response_id),
    dimension    TEXT,
    score        INTEGER,
    PRIMARY KEY (response_id, dimension)
);

CREATE TABLE comments (
    response_id  TEXT PRIMARY KEY REFERENCES respondents(response_id),
    comment      TEXT
);
