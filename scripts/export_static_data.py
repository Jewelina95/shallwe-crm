"""Export the local SQLite CRM into a private JS data file for the static CRM.

The generated file contains PII and is intentionally ignored by git:
    web/data/contacts.private.js
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "crm.db"
OUT_PATH = ROOT / "web" / "data" / "contacts.private.js"


def rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    contacts = rows(conn, "SELECT * FROM contacts ORDER BY updated_at DESC")
    events = rows(conn, "SELECT * FROM events ORDER BY date DESC")
    attendance = rows(
        conn,
        """
        SELECT ea.*, e.name AS event_name, e.date AS event_date
        FROM event_attendance ea
        JOIN events e ON e.id = ea.event_id
        ORDER BY ea.registered_at DESC
        """,
    )

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "contacts": contacts,
        "events": events,
        "attendance": attendance,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        "window.SHALLWE_PRIVATE_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Exported {len(contacts)} contacts, {len(events)} events, {len(attendance)} attendance rows")
    print(OUT_PATH)


if __name__ == "__main__":
    main()
