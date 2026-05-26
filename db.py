"""SQLite database layer — stores raw articles and extracted cases."""

import sqlite3
import json
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    # 1. Base tables (CREATE IF NOT EXISTS is safe to re-run)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            url            TEXT    UNIQUE NOT NULL,
            source         TEXT    NOT NULL,
            title          TEXT,
            published_date TEXT,
            content        TEXT,
            scraped_at     TEXT    DEFAULT (datetime('now')),
            processed      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cases (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id                  INTEGER REFERENCES articles(id),
            source                      TEXT,
            article_url                 TEXT,
            article_title               TEXT,
            published_date              TEXT,
            incident_date               TEXT,
            district                    TEXT,
            upazila                     TEXT,
            gang_rape                   INTEGER DEFAULT 0,
            victim_count                INTEGER DEFAULT 1,
            victim_age                  INTEGER,
            victim_age_group            TEXT,
            perpetrator_count           INTEGER DEFAULT 1,
            case_filed                  INTEGER DEFAULT 0,
            arrest_made                 INTEGER DEFAULT 0,
            keywords_matched            TEXT,
            extracted_at                TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # 2. Migrate: add any new columns that don't exist yet
    _migrate(conn)

    # 3. Indexes — safe after migration ensures all columns exist
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_articles_source   ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_date     ON articles(published_date);
        CREATE INDEX IF NOT EXISTS idx_cases_district    ON cases(district);
        CREATE INDEX IF NOT EXISTS idx_cases_date        ON cases(published_date);
        CREATE INDEX IF NOT EXISTS idx_cases_perp_type   ON cases(perp_relationship);
        CREATE INDEX IF NOT EXISTS idx_cases_victim_age  ON cases(victim_age);
    """)
    conn.commit()
    conn.close()


def _migrate(conn: sqlite3.Connection):
    """Add any columns present in the schema but missing from an older DB."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(cases)")}
    new_cols = {
        "location_type":             "TEXT",
        "incident_setting":          "TEXT",
        "incident_time_of_day":      "TEXT",
        "incident_method":           "TEXT",
        "victim_gender":             "TEXT",
        "victim_occupation":         "TEXT",
        "victim_religion":           "TEXT",
        "victim_marital_status":     "TEXT",
        "victim_disability":         "INTEGER DEFAULT 0",
        "victim_knew_perpetrator":   "INTEGER",
        "victim_killed_after":       "INTEGER DEFAULT 0",
        "victim_suicide":            "INTEGER DEFAULT 0",
        "perp_age":                  "INTEGER",
        "perp_age_group":            "TEXT",
        "perp_gender":               "TEXT DEFAULT 'male'",
        "perp_occupation":           "TEXT",
        "perp_relationship":         "TEXT",
        "perp_political_connection": "INTEGER DEFAULT 0",
        "perp_prior_record":         "INTEGER DEFAULT 0",
        "perp_used_weapon":          "INTEGER DEFAULT 0",
        "perp_used_intoxicant":      "INTEGER DEFAULT 0",
        "perp_local_influence":      "INTEGER DEFAULT 0",
        "psych_power_motive":        "INTEGER DEFAULT 0",
        "psych_opportunistic":       "INTEGER DEFAULT 0",
        "psych_premeditated":        "INTEGER DEFAULT 0",
        "psych_revenge_motive":      "INTEGER DEFAULT 0",
        "trial_mentioned":           "INTEGER DEFAULT 0",
        "conviction_mentioned":      "INTEGER DEFAULT 0",
        # rename old column
        "perp_relationship":         "TEXT",
    }
    for col, dtype in new_cols.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE cases ADD COLUMN {col} {dtype}")
                conn.commit()
            except sqlite3.OperationalError:
                pass


def article_exists(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM articles WHERE url=?", (url,)).fetchone()
        return row is not None


def save_article(source: str, url: str, title: str, date: str, content: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO articles (source, url, title, published_date, content)
               VALUES (?, ?, ?, ?, ?)""",
            (source, url, title, date, content),
        )


def get_unprocessed_articles():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM articles WHERE processed=0"
        ).fetchall()


def mark_processed(article_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE articles SET processed=1 WHERE id=?", (article_id,))


def save_case(case: dict):
    cols = ", ".join(case.keys())
    placeholders = ", ".join(f":{k}" for k in case.keys())
    with get_conn() as conn:
        conn.execute(f"INSERT INTO cases ({cols}) VALUES ({placeholders})", case)


def get_stats() -> dict:
    with get_conn() as conn:
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        cases    = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        sources  = conn.execute(
            "SELECT source, COUNT(*) as n FROM articles GROUP BY source"
        ).fetchall()
        return {
            "total_articles": articles,
            "total_cases":    cases,
            "by_source":      {r["source"]: r["n"] for r in sources},
        }
