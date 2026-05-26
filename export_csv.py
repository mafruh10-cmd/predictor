"""Export the cases table to CSV."""

import csv
import sqlite3
from config import DB_PATH, CSV_PATH


def export():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM cases ORDER BY published_date").fetchall()
    if not rows:
        print("No cases to export yet.")
        return

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])

    print(f"Exported {len(rows)} cases → {CSV_PATH}")
    conn.close()


if __name__ == "__main__":
    export()
