"""Contacts page - HubSpot-style audience browser with filters and detail drawer."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st

import db
from keywords import extract_interests

st.set_page_config(page_title="Contacts · ShallWe CRM", page_icon="👥", layout="wide")
db.init_db()

st.title("👥 Contacts")
st.caption("Search, segment, and drill into your audience.")

# ---- Sidebar filters ----
all_contacts = db.list_contacts()
df_all = pd.DataFrame(all_contacts) if all_contacts else pd.DataFrame()

with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search", placeholder="name, email, org…")
    pro_options = ["All"] + sorted(
        [x for x in (df_all.get("professional_category", pd.Series()).dropna().unique() if not df_all.empty else []) if x]
    )
    pro = st.selectbox("Professional category", pro_options)
    events = db.list_events()
    event_lookup = {"All": None, **{e["name"]: e["id"] for e in events}}
    sel_event = st.selectbox("Attended event", list(event_lookup.keys()))
    mandarin_only = st.checkbox("Mandarin speakers only")

filters = {
    "search": search,
    "professional_category": pro,
    "event_id": event_lookup[sel_event],
    "mandarin_only": mandarin_only,
}
contacts = db.list_contacts(filters)

# ---- Build display dataframe with engagement score ----
if contacts:
    df = pd.DataFrame(contacts)
    # attendance counts per contact
    with db.get_conn() as conn:
        att_counts = pd.read_sql_query(
            "SELECT contact_id, COUNT(*) AS events_attended, "
            "SUM(CASE WHEN approval_status='approved' THEN 1 ELSE 0 END) AS approved_count, "
            "SUM(CASE WHEN checked_in_at IS NOT NULL AND checked_in_at != '' THEN 1 ELSE 0 END) AS checkin_count "
            "FROM event_attendance GROUP BY contact_id",
            conn,
        )
    df = df.merge(att_counts, left_on="id", right_on="contact_id", how="left").fillna(
        {"events_attended": 0, "approved_count": 0, "checkin_count": 0}
    )
    df["engagement"] = (
        df["events_attended"].astype(int)
        + df["approved_count"].astype(int)
        + df["checkin_count"].astype(int) * 2
    )
else:
    df = pd.DataFrame()

st.subheader(f"{len(df):,} contacts")

if df.empty:
    st.info("No contacts match. Go to **Settings → Import** to load your Luma xlsx, or clear filters.")
else:
    show = df[[
        "id", "full_name", "email", "professional_category", "organization",
        "role_title", "events_attended", "engagement", "mandarin_speaker", "linkedin",
    ]].rename(columns={
        "full_name": "Name",
        "email": "Email",
        "professional_category": "Category",
        "organization": "Organization",
        "role_title": "Role",
        "events_attended": "Events",
        "engagement": "Score",
        "mandarin_speaker": "中文",
        "linkedin": "LinkedIn",
    })
    show["中文"] = show["中文"].apply(lambda x: "✅" if x else "")
    st.dataframe(
        show.drop(columns=["id"]),
        use_container_width=True,
        hide_index=True,
        height=480,
    )

    # Export
    csv = show.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export filtered to CSV", csv, "contacts_export.csv", "text/csv")

    st.divider()

    # ---- Detail drawer ----
    st.subheader("Contact detail")
    name_to_id = {f"{r['full_name'] or '(no name)'} · {r['email']}": int(r["id"]) for _, r in df.iterrows()}
    pick = st.selectbox("Select a contact", list(name_to_id.keys()))
    if pick:
        cid = name_to_id[pick]
        c = db.get_contact(cid)
        att = db.get_attendance_for_contact(cid)
        col_a, col_b = st.columns([2, 3])
        with col_a:
            st.markdown(f"### {c.get('full_name') or '(no name)'}")
            st.markdown(f"**📧** {c['email']}")
            if c.get("linkedin"):
                st.markdown(f"**🔗** {c['linkedin']}")
            if c.get("phone"):
                st.markdown(f"**📞** {c['phone']}")
            if c.get("organization"):
                st.markdown(f"**🏢** {c['organization']}")
            if c.get("role_title"):
                st.markdown(f"**💼** {c['role_title']}")
            if c.get("professional_category"):
                st.markdown(f"**🏷️** {c['professional_category']}")
            if c.get("mandarin_speaker"):
                st.markdown("**🀄** Speaks Mandarin")
            st.markdown(f"**Source:** {c.get('source') or '—'}")

            # Derived interests across all attendance free-text
            blob = " ".join(
                str(a.get(k) or "")
                for a in att
                for k in ("motivation", "questions_for_speakers", "experience")
            )
            blob += " " + " ".join(filter(None, [c.get("role_title"), c.get("professional_category"), c.get("organization")]))
            tags = extract_interests(blob)
            if tags:
                st.markdown("**Inferred interests:** " + " ".join(f"`{t}`" for t in tags))

            with st.expander("Edit notes / tags"):
                notes = st.text_area("Notes", value=c.get("notes") or "")
                tags_in = st.text_input("Manual tags (comma-sep)", value=c.get("tags") or "")
                if st.button("Save", key=f"save_{cid}"):
                    db.upsert_contact({"email": c["email"], "notes": notes, "tags": tags_in})
                    st.success("Saved.")
                    st.rerun()

        with col_b:
            st.markdown("### Event timeline")
            if not att:
                st.caption("No event attendance yet.")
            for a in att:
                with st.expander(f"📅 {a['event_name']} — {a.get('approval_status') or 'n/a'}"):
                    st.write(f"**Registered:** {a.get('registered_at') or '—'}")
                    st.write(f"**Checked in:** {a.get('checked_in_at') or '—'}")
                    st.write(f"**Ticket:** {a.get('ticket_name') or '—'}  |  **Paid:** {a.get('amount_paid') or '—'}")
                    if a.get("experience"):
                        st.markdown(f"**Experience**\n\n> {a['experience']}")
                    if a.get("motivation"):
                        st.markdown(f"**Motivation to join**\n\n> {a['motivation']}")
                    if a.get("questions_for_speakers"):
                        st.markdown(f"**Questions for speakers**\n\n> {a['questions_for_speakers']}")
                    if a.get("custom_data"):
                        try:
                            extra = json.loads(a["custom_data"])
                            if extra:
                                st.markdown("**Other form fields**")
                                st.json(extra)
                        except Exception:
                            pass

st.divider()
with st.expander("➕ Add a contact manually"):
    with st.form("add_contact"):
        c1, c2 = st.columns(2)
        email = c1.text_input("Email *")
        full_name = c2.text_input("Full name")
        first_name = c1.text_input("First name")
        last_name = c2.text_input("Last name")
        org = c1.text_input("Organization")
        role = c2.text_input("Role / title")
        cat = c1.selectbox(
            "Professional category",
            ["", "Academic Researcher", "Enterprise Professional", "Student", "Investor", "Founder", "Other"],
        )
        linkedin = c2.text_input("LinkedIn URL")
        mandarin = st.checkbox("Speaks Mandarin")
        tags_in = st.text_input("Tags (comma-sep)")
        notes = st.text_area("Notes")
        submit = st.form_submit_button("Create contact")
        if submit and email:
            db.upsert_contact({
                "email": email,
                "full_name": full_name or f"{first_name} {last_name}".strip(),
                "first_name": first_name, "last_name": last_name,
                "organization": org, "role_title": role,
                "professional_category": cat, "linkedin": linkedin,
                "mandarin_speaker": 1 if mandarin else 0,
                "tags": tags_in, "notes": notes, "source": "manual",
            })
            st.success("Contact created.")
            st.rerun()
