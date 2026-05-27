"""SQLite layer for ShallWe Tech CRM."""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    phone TEXT,
    linkedin TEXT,
    company_website TEXT,
    organization TEXT,
    role_title TEXT,
    professional_category TEXT,
    city TEXT,
    country TEXT,
    mandarin_speaker INTEGER DEFAULT 0,
    interests TEXT,
    source TEXT,
    notes TEXT,
    tags TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    date TEXT,
    description TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS event_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    api_id TEXT,
    approval_status TEXT,
    ticket_name TEXT,
    amount_paid TEXT,
    checked_in_at TEXT,
    registered_at TEXT,
    motivation TEXT,
    questions_for_speakers TEXT,
    experience TEXT,
    custom_data TEXT,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    UNIQUE(contact_id, event_id)
);

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    to_email TEXT,
    subject TEXT,
    body TEXT,
    status TEXT,
    error TEXT,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    subject TEXT,
    body TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        ensure_columns(conn)
        # Seed default templates if empty
        cur = conn.execute("SELECT COUNT(*) AS c FROM email_templates")
        if cur.fetchone()["c"] == 0:
            now = datetime.utcnow().isoformat()
            for name, subj, body in DEFAULT_TEMPLATES:
                conn.execute(
                    "INSERT INTO email_templates(name,subject,body,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (name, subj, body, now, now),
                )


def ensure_columns(conn):
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(contacts)").fetchall()}
    if "company_website" not in existing:
        conn.execute("ALTER TABLE contacts ADD COLUMN company_website TEXT")


DEFAULT_TEMPLATES = [
    (
        "Forum Invitation (EN)",
        "You're invited: ShallWe Tech AI Forum",
        "Hi {{first_name}},\n\nWe'd love to invite you to our upcoming ShallWe Tech AI Forum. Based on your background at {{organization}}, we think the discussions on World Models, Agents, and AI productization will resonate with you.\n\nDate: TBD\nLocation: TBD\n\nRSVP: <link>\n\nBest,\nShallWe Tech Team",
    ),
    (
        "论坛邀请（中文）",
        "ShallWe Tech AI 论坛邀请",
        "{{first_name}} 你好，\n\n我们想邀请你参加即将举办的 ShallWe Tech AI 论坛。基于你在 {{organization}} 的背景，相信关于世界模型、Agent 与 AI 产业化的讨论会让你感兴趣。\n\n时间：待定\n地点：待定\n\nRSVP：<链接>\n\n祝好，\nShallWe Tech",
    ),
    (
        "Follow-up after event",
        "Thanks for joining {{event_name}}",
        "Hi {{first_name}},\n\nThank you for joining us at {{event_name}}. We'd love to hear your feedback and stay connected.\n\nIf you'd like to be involved in future events or speak at one, just reply to this email.\n\nBest,\nShallWe Tech",
    ),
]


# -------- Contacts --------
def upsert_contact(data: dict) -> int:
    """Insert or update by email. Returns contact_id."""
    now = datetime.utcnow().isoformat()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise ValueError("email required")
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM contacts WHERE email = ?", (email,))
        row = cur.fetchone()
        fields = [
            "first_name", "last_name", "full_name", "phone", "linkedin", "company_website",
            "organization", "role_title", "professional_category",
            "city", "country", "mandarin_speaker", "interests",
            "source", "notes", "tags",
        ]
        if row:
            cid = row["id"]
            sets = []
            vals = []
            for f in fields:
                if data.get(f) not in (None, ""):
                    sets.append(f"{f} = ?")
                    vals.append(data[f])
            if sets:
                sets.append("updated_at = ?")
                vals.append(now)
                vals.append(cid)
                conn.execute(f"UPDATE contacts SET {', '.join(sets)} WHERE id = ?", vals)
            return cid
        else:
            cols = ["email"] + fields + ["created_at", "updated_at"]
            vals = [email] + [data.get(f) for f in fields] + [now, now]
            placeholders = ",".join(["?"] * len(cols))
            cur = conn.execute(
                f"INSERT INTO contacts({','.join(cols)}) VALUES({placeholders})",
                vals,
            )
            return cur.lastrowid


def list_contacts(filters: dict | None = None) -> list[dict]:
    sql = "SELECT * FROM contacts"
    args = []
    where = []
    if filters:
        for k, v in filters.items():
            if v in (None, "", "All"):
                continue
            if k == "search":
                where.append("(LOWER(full_name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(organization) LIKE ?)")
                like = f"%{v.lower()}%"
                args.extend([like, like, like])
            elif k == "professional_category":
                where.append("professional_category = ?")
                args.append(v)
            elif k == "mandarin_only" and v:
                where.append("mandarin_speaker = 1")
            elif k == "event_id":
                where.append("id IN (SELECT contact_id FROM event_attendance WHERE event_id = ?)")
                args.append(v)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_contact(cid: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (cid,)).fetchone()
        return dict(row) if row else None


def delete_contact(cid: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM event_attendance WHERE contact_id = ?", (cid,))
        conn.execute("DELETE FROM contacts WHERE id = ?", (cid,))


# -------- Events --------
def upsert_event(name: str, date: str | None = None, description: str | None = None) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM events WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO events(name,date,description,created_at) VALUES(?,?,?,?)",
            (name, date, description, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_events() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM events ORDER BY date DESC").fetchall()]


def upsert_attendance(contact_id: int, event_id: int, data: dict):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM event_attendance WHERE contact_id=? AND event_id=?",
            (contact_id, event_id),
        ).fetchone()
        fields = ["api_id", "approval_status", "ticket_name", "amount_paid",
                  "checked_in_at", "registered_at", "motivation",
                  "questions_for_speakers", "experience", "custom_data"]
        if row:
            sets = []
            vals = []
            for f in fields:
                if data.get(f) not in (None, ""):
                    sets.append(f"{f} = ?")
                    vals.append(data[f])
            if sets:
                vals.append(row["id"])
                conn.execute(f"UPDATE event_attendance SET {', '.join(sets)} WHERE id = ?", vals)
        else:
            cols = ["contact_id", "event_id"] + fields
            vals = [contact_id, event_id] + [data.get(f) for f in fields]
            placeholders = ",".join(["?"] * len(cols))
            conn.execute(
                f"INSERT INTO event_attendance({','.join(cols)}) VALUES({placeholders})",
                vals,
            )


def get_attendance_for_contact(contact_id: int) -> list[dict]:
    sql = """
    SELECT ea.*, e.name AS event_name, e.date AS event_date
    FROM event_attendance ea
    JOIN events e ON e.id = ea.event_id
    WHERE ea.contact_id = ?
    ORDER BY e.date DESC
    """
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (contact_id,)).fetchall()]


# -------- Email log + templates --------
def log_email(contact_id: int | None, to_email: str, subject: str, body: str, status: str, error: str | None = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO email_log(contact_id,to_email,subject,body,status,error,sent_at) VALUES(?,?,?,?,?,?,?)",
            (contact_id, to_email, subject, body, status, error, datetime.utcnow().isoformat()),
        )


def list_email_log(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM email_log ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()]


def list_templates() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM email_templates ORDER BY name").fetchall()]


def save_template(name: str, subject: str, body: str, template_id: int | None = None):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        if template_id:
            conn.execute(
                "UPDATE email_templates SET name=?, subject=?, body=?, updated_at=? WHERE id=?",
                (name, subject, body, now, template_id),
            )
        else:
            conn.execute(
                "INSERT INTO email_templates(name,subject,body,created_at,updated_at) VALUES(?,?,?,?,?)",
                (name, subject, body, now, now),
            )


def delete_template(template_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))


# -------- Settings (SMTP creds) --------
def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def recompute_all_interests() -> int:
    """Re-extract interests for every contact based on profile + attendance free-text.

    Returns number of contacts updated.
    """
    from keywords import extract_interests
    updated = 0
    with get_conn() as conn:
        contacts = conn.execute("SELECT id, role_title, organization, professional_category FROM contacts").fetchall()
        for c in contacts:
            att = conn.execute(
                "SELECT motivation, questions_for_speakers, experience FROM event_attendance WHERE contact_id = ?",
                (c["id"],),
            ).fetchall()
            blob = " ".join(filter(None, [c["role_title"], c["organization"], c["professional_category"]]))
            for a in att:
                blob += " " + " ".join(filter(None, [a["motivation"], a["questions_for_speakers"], a["experience"]]))
            tags = extract_interests(blob)
            tag_str = ",".join(tags)
            conn.execute("UPDATE contacts SET interests = ? WHERE id = ?", (tag_str, c["id"]))
            updated += 1
    return updated


def all_interest_tags() -> list[str]:
    """Distinct interest tags currently stored across all contacts."""
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT interests FROM contacts WHERE interests IS NOT NULL AND interests != ''").fetchall()
    tags = set()
    for r in rows:
        for t in (r["interests"] or "").split(","):
            t = t.strip()
            if t:
                tags.add(t)
    return sorted(tags)


def stats() -> dict:
    with get_conn() as conn:
        c = conn.execute("SELECT COUNT(*) AS c FROM contacts").fetchone()["c"]
        e = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        a = conn.execute("SELECT COUNT(*) AS c FROM event_attendance").fetchone()["c"]
        m = conn.execute("SELECT COUNT(*) AS c FROM contacts WHERE mandarin_speaker = 1").fetchone()["c"]
        return {"contacts": c, "events": e, "attendance": a, "mandarin": m}
