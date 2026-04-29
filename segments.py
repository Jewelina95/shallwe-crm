"""Shared segment-building logic used by Contacts, Analytics, and Email pages.

Centralizes:
- Loading the contact list joined with attendance counts and event names
- Applying multi-dimensional filters
- Building the final export-ready dataframe (xlsx-friendly column names)
"""
from __future__ import annotations
from io import BytesIO

import pandas as pd

import db


def enriched_contacts() -> pd.DataFrame:
    """All contacts + attendance summary as a single dataframe."""
    rows = db.list_contacts()
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if df.empty:
        return df

    with db.get_conn() as conn:
        att = pd.read_sql_query(
            """
            SELECT ea.contact_id,
                   COUNT(*) AS events_attended,
                   GROUP_CONCAT(DISTINCT e.name) AS event_names,
                   MAX(ea.registered_at) AS last_registered_at,
                   GROUP_CONCAT(DISTINCT ea.approval_status) AS approval_statuses,
                   SUM(CASE WHEN ea.checked_in_at IS NOT NULL AND ea.checked_in_at != '' THEN 1 ELSE 0 END) AS checkin_count
            FROM event_attendance ea
            JOIN events e ON e.id = ea.event_id
            GROUP BY ea.contact_id
            """,
            conn,
        )

    df = df.merge(att, left_on="id", right_on="contact_id", how="left")
    df["events_attended"] = df["events_attended"].fillna(0).astype(int)
    df["checkin_count"] = df["checkin_count"].fillna(0).astype(int)
    df["event_names"] = df["event_names"].fillna("")
    df["approval_statuses"] = df["approval_statuses"].fillna("")
    df["interests"] = df["interests"].fillna("")
    df["organization"] = df["organization"].fillna("")
    df["professional_category"] = df["professional_category"].fillna("")
    df["source"] = df["source"].fillna("")
    df["mandarin_speaker"] = df["mandarin_speaker"].fillna(0).astype(int)
    df["linkedin"] = df["linkedin"].fillna("")
    df["engagement_score"] = (
        df["events_attended"] + df["checkin_count"] * 2
    ).astype(int)
    return df


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Apply a filter dict produced by the UI to the enriched dataframe."""
    if df.empty:
        return df
    out = df

    search = (f.get("search") or "").strip().lower()
    if search:
        mask = (
            out["full_name"].fillna("").str.lower().str.contains(search, na=False)
            | out["email"].fillna("").str.lower().str.contains(search, na=False)
            | out["organization"].str.lower().str.contains(search, na=False)
            | out["role_title"].fillna("").str.lower().str.contains(search, na=False)
        )
        out = out[mask]

    cats = f.get("professional_categories") or []
    if cats:
        out = out[out["professional_category"].isin(cats)]

    interests = f.get("interest_tags") or []
    if interests:
        # Match if contact's interests column contains ANY of the selected tags
        pattern = "|".join(map(_re_escape, interests))
        out = out[out["interests"].str.contains(pattern, case=False, na=False, regex=True)]

    orgs = f.get("organizations") or []
    if orgs:
        out = out[out["organization"].isin(orgs)]

    event_ids = f.get("event_ids") or []
    if event_ids:
        # event_ids -> event names via current events list
        events = {e["id"]: e["name"] for e in db.list_events()}
        wanted_names = {events[i] for i in event_ids if i in events}
        out = out[out["event_names"].apply(
            lambda s: any(n in (s or "") for n in wanted_names)
        )]

    sources = f.get("sources") or []
    if sources:
        out = out[out["source"].isin(sources)]

    if f.get("mandarin_only"):
        out = out[out["mandarin_speaker"] == 1]
    if f.get("non_mandarin_only"):
        out = out[out["mandarin_speaker"] == 0]
    if f.get("has_linkedin"):
        out = out[out["linkedin"].str.strip() != ""]

    min_e = f.get("min_events_attended") or 0
    if min_e:
        out = out[out["events_attended"] >= min_e]

    approval = f.get("approval_status")
    if approval:
        out = out[out["approval_statuses"].str.contains(approval, case=False, na=False)]

    return out


def _re_escape(s: str) -> str:
    import re
    return re.escape(s)


# Columns shown in UI tables and emitted to xlsx
EXPORT_COLUMNS = [
    "full_name", "email", "phone", "linkedin",
    "professional_category", "organization", "role_title",
    "interests", "mandarin_speaker",
    "events_attended", "event_names", "approval_statuses", "checkin_count",
    "engagement_score", "source",
    "last_registered_at", "tags", "notes",
    "created_at",
]

EXPORT_RENAME = {
    "full_name": "Name",
    "email": "Email",
    "phone": "Phone",
    "linkedin": "LinkedIn",
    "professional_category": "Professional Category",
    "organization": "Organization",
    "role_title": "Role / Title",
    "interests": "Interests",
    "mandarin_speaker": "Mandarin",
    "events_attended": "Events Attended",
    "event_names": "Event Names",
    "approval_statuses": "Approval Status",
    "checkin_count": "Check-ins",
    "engagement_score": "Engagement Score",
    "source": "Source",
    "last_registered_at": "Last Registered",
    "tags": "Manual Tags",
    "notes": "Notes",
    "created_at": "Created",
}


def to_export_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(EXPORT_RENAME.values()))
    cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    out = df[cols].copy().rename(columns=EXPORT_RENAME)
    if "Mandarin" in out.columns:
        out["Mandarin"] = out["Mandarin"].map({1: "Yes", 0: ""})
    return out


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Contacts") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        # Auto-size columns (cap at 60)
        for col_cells in ws.columns:
            max_len = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
            letter = col_cells[0].column_letter
            ws.column_dimensions[letter].width = min(max(12, max_len + 2), 60)
    return buf.getvalue()
