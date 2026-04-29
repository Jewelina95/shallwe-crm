"""Import the existing Luma attendance xlsx into the CRM database.

Usage:
    python import_excel.py "/path/to/ShallWe Tech - Pat Attendance List.xlsx"

Auto-detects sheets and merges rows by email (one contact, many event attendances).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd

import db
from keywords import extract_interests


# Sheet -> event metadata. Update this if you add new sheets.
SHEET_TO_EVENT = {
    "Luma List": {"name": "AI Forum (Luma)", "date": "2026-01-15", "description": "ShallWe Tech AI Forum - Luma registration"},
    "Tare": {"name": "Vibe Coding Workshop (Tare)", "date": "2026-03-20", "description": "Vibe Coding Workshop"},
}


def _str(x):
    if x is None:
        return None
    if isinstance(x, float) and pd.isna(x):
        return None
    s = str(x).strip()
    return s or None


def _bool_zh(x):
    s = _str(x)
    return 1 if s in ("是", "Yes", "yes", "Y", "true", "True", "1") else 0


def import_luma_sheet(df: pd.DataFrame, event_name: str, event_date: str, event_desc: str):
    event_id = db.upsert_event(event_name, event_date, event_desc)
    inserted = 0
    skipped = 0
    for _, r in df.iterrows():
        email = _str(r.get("email"))
        if not email:
            skipped += 1
            continue

        # Pick form-input first name if available, else luma's first name
        first_name = (
            _str(r.get("First Name(Same as your ID)"))
            or _str(r.get("First Name (The Same as your ID)"))
            or _str(r.get("first_name"))
        )
        last_name = (
            _str(r.get("Last Name(Same as your ID)"))
            or _str(r.get("Last Name (The Same as your ID)"))
            or _str(r.get("last_name"))
        )
        full_name = _str(r.get("name")) or " ".join(filter(None, [first_name, last_name]))

        organization = (
            _str(r.get("Which Organization You Work For"))
            or _str(r.get("What company/organization do you work for?"))
        )
        role_title = (
            _str(r.get("Your Role/Job Title"))
            or _str(r.get("What's your professional?"))
        )
        professional = _str(r.get("Your Professional"))
        linkedin = _str(r.get("Your Linkedin Profile?"))
        phone = _str(r.get("phone_number"))
        mandarin = _bool_zh(r.get("Please Confirm you can speak Mandarin!"))
        utm = _str(r.get("utm_source"))

        # Extract interests from this row's free-text answers + profile
        text_for_tags = " ".join(filter(None, [
            _str(r.get("Tell us your experience in AI/Tech field")),
            _str(r.get("What is your experience level with Vibe Coding")),
            _str(r.get("What drive you to join this event?")),
            _str(r.get("What questions you have for our speakers?")),
            role_title, organization, professional,
        ]))
        new_tags = set(extract_interests(text_for_tags))

        contact_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "phone": phone,
            "linkedin": linkedin,
            "organization": organization,
            "role_title": role_title,
            "professional_category": professional,
            "mandarin_speaker": mandarin,
            "source": utm or "luma",
        }
        cid = db.upsert_contact(contact_data)

        # Merge interests with whatever was previously stored (so multi-event signals accumulate)
        if new_tags:
            existing = db.get_contact(cid).get("interests") or ""
            existing_set = {t.strip() for t in existing.split(",") if t.strip()}
            merged = sorted(existing_set | new_tags)
            db.upsert_contact({"email": email, "interests": ",".join(merged)})

        # Build custom data: stash everything that didn't fit into a standard column
        custom = {}
        for col in df.columns:
            if col in {
                "api_id", "name", "first_name", "last_name", "email", "phone_number",
                "created_at", "approval_status", "checked_in_at", "utm_source",
                "qr_code_url", "amount", "amount_tax", "amount_discount", "currency",
                "ticket_type_id", "ticket_name",
                "First Name(Same as your ID)", "Last Name(Same as your ID)",
                "First Name (The Same as your ID)", "Last Name (The Same as your ID)",
                "Your Professional", "Which Organization You Work For",
                "Your Role/Job Title",
                "What company/organization do you work for?",
                "What's your professional?",
                "Please Confirm you can speak Mandarin!",
                "Your Linkedin Profile?",
            }:
                continue
            v = _str(r.get(col))
            if v:
                custom[col] = v

        amt = _str(r.get("amount"))
        att = {
            "api_id": _str(r.get("api_id")),
            "approval_status": _str(r.get("approval_status")),
            "ticket_name": _str(r.get("ticket_name")),
            "amount_paid": amt,
            "checked_in_at": _str(r.get("checked_in_at")),
            "registered_at": _str(r.get("created_at")),
            "motivation": _str(r.get("What drive you to join this event?")),
            "questions_for_speakers": _str(r.get("What questions you have for our speakers?")),
            "experience": (
                _str(r.get("Tell us your experience in AI/Tech field"))
                or _str(r.get("What is your experience level with Vibe Coding"))
            ),
            "custom_data": json.dumps(custom, ensure_ascii=False) if custom else None,
        }
        db.upsert_attendance(cid, event_id, att)
        inserted += 1
    return inserted, skipped


def import_non_luma_emails(df: pd.DataFrame):
    inserted = 0
    skipped = 0
    # the column header itself is an email — include it as a row
    rows = list(df.iloc[:, 0].astype(str)) + [df.columns[0]]
    for raw in rows:
        email = _str(raw)
        if not email or "@" not in email:
            skipped += 1
            continue
        try:
            db.upsert_contact({"email": email, "source": "non-luma"})
            inserted += 1
        except Exception:
            skipped += 1
    return inserted, skipped


def import_xlsx(path: str | Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    db.init_db()
    xl = pd.ExcelFile(path)
    summary = {}
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        if sheet in SHEET_TO_EVENT:
            meta = SHEET_TO_EVENT[sheet]
            ins, skp = import_luma_sheet(df, meta["name"], meta["date"], meta["description"])
            summary[sheet] = {"event": meta["name"], "imported": ins, "skipped": skp}
        elif sheet.lower().startswith("non-luma") or "@" in str(df.columns[0]):
            ins, skp = import_non_luma_emails(df)
            summary[sheet] = {"event": None, "imported": ins, "skipped": skp}
        else:
            summary[sheet] = {"event": None, "imported": 0, "skipped": len(df), "note": "unknown sheet"}
    return summary


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "/Users/wenshaoyue/Desktop/shallwetech/ShallWe Tech - Pat Attendance List.xlsx"
    res = import_xlsx(p)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("Stats:", db.stats())
