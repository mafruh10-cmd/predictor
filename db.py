"""SQLite database layer — stores raw articles and extracted cases."""

import sqlite3
import json
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                url           TEXT    UNIQUE NOT NULL,
                source        TEXT    NOT NULL,
                title         TEXT,
                published_date TEXT,
                content       TEXT,
                scraped_at    TEXT    DEFAULT (datetime('now')),
                processed     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cases (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id             INTEGER REFERENCES articles(id),
                source                 TEXT,
                article_url            TEXT,
                article_title          TEXT,
                published_date         TEXT,
                incident_date          TEXT,
                district               TEXT,
                upazila                TEXT,
                victim_age             INTEGER,
                victim_age_group       TEXT,
                victim_count           INTEGER DEFAULT 1,
                perpetrator_count      INTEGER DEFAULT 1,
                perpetrator_type       TEXT,
                gang_rape              INTEGER DEFAULT 0,
                case_filed             INTEGER DEFAULT 0,
                arrest_made            INTEGER DEFAULT 0,
                keywords_matched       TEXT,
                extracted_at           TEXT    DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
            CREATE INDEX IF NOT EXISTS idx_articles_date   ON articles(published_date);
            CREATE INDEX IF NOT EXISTS idx_cases_district  ON cases(district);
            CREATE INDEX IF NOT EXISTS idx_cases_date      ON cases(published_date);
        """)


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
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO cases (
                article_id, source, article_url, article_title, published_date,
                incident_date, district, upazila, victim_age, victim_age_group,
                victim_count, perpetrator_count, perpetrator_type, gang_rape,
                case_filed, arrest_made, keywords_matched
               ) VALUES (
                :article_id, :source, :article_url, :article_title, :published_date,
                :incident_date, :district, :upazila, :victim_age, :victim_age_group,
                :victim_count, :perpetrator_count, :perpetrator_type, :gang_rape,
                :case_filed, :arrest_made, :keywords_matched
               )""",
            case,
        )


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
