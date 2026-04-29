"""Contacts page - powerful multi-filter audience browser with Excel export."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st

import db
from keywords import extract_interests
import segments

st.set_page_config(page_title="Contacts · ShallWe CRM", page_icon="👥", layout="wide")
db.init_db()

st.title("👥 Contacts")
st.caption("Filter by interest, profession, organization, event, source… then download as Excel.")

df_full = segments.enriched_contacts()
if df_full.empty:
    st.warning("No contacts yet. Go to **Settings → Import** first.")
    st.stop()

# ---- Sidebar filters ----
all_interests = db.all_interest_tags()
all_pros = sorted(x for x in df_full["professional_category"].unique() if x)
all_orgs = sorted(x for x in df_full["organization"].unique() if x)
all_sources = sorted(x for x in df_full["source"].unique() if x)
events = db.list_events()
event_options = {e["name"]: e["id"] for e in events}

with st.sidebar:
    st.header("🔍 Filters")
    search = st.text_input("Search", placeholder="name, email, org, role…")

    interest_tags = st.multiselect(
        "Interests (any of)",
        options=all_interests,
        help="Auto-extracted from registration answers + profile.",
    )
    pro_cats = st.multiselect("Professional category", options=all_pros)
    pick_events = st.multiselect("Attended event", options=list(event_options.keys()))
    pick_orgs = st.multiselect("Organization", options=all_orgs)
    pick_sources = st.multiselect("Source / channel", options=all_sources)

    st.divider()
    mandarin = st.radio("Language", ["Any", "Mandarin only", "Non-Mandarin only"], horizontal=False)
    has_linkedin = st.checkbox("Has LinkedIn URL")
    min_events = st.slider("Min events attended", 0, max(int(df_full["events_attended"].max() or 0), 1), 0)
    approval = st.selectbox("Approval status (any event)", ["", "approved", "declined", "waitlist", "pending"])

filters = {
    "search": search,
    "interest_tags": interest_tags,
    "professional_categories": pro_cats,
    "event_ids": [event_options[n] for n in pick_events],
    "organizations": pick_orgs,
    "sources": pick_sources,
    "mandarin_only": mandarin == "Mandarin only",
    "non_mandarin_only": mandarin == "Non-Mandarin only",
    "has_linkedin": has_linkedin,
    "min_events_attended": min_events,
    "approval_status": approval or None,
}

filtered = segments.apply_filters(df_full, filters)

# ---- Filter chips ----
active_chips = []
if interest_tags: active_chips.append(f"💡 {len(interest_tags)} interests")
if pro_cats:      active_chips.append(f"🏷️ {len(pro_cats)} categories")
if pick_events:   active_chips.append(f"📅 {len(pick_events)} events")
if pick_orgs:     active_chips.append(f"🏢 {len(pick_orgs)} orgs")
if pick_sources:  active_chips.append(f"📥 {len(pick_sources)} sources")
if mandarin != "Any": active_chips.append(f"🀄 {mandarin}")
if has_linkedin:  active_chips.append("🔗 has LinkedIn")
if min_events:    active_chips.append(f"🎯 ≥{min_events} events")
if approval:      active_chips.append(f"✅ approval: {approval}")
if search:        active_chips.append(f"🔎 '{search}'")

c_top1, c_top2 = st.columns([3, 2])
c_top1.subheader(f"{len(filtered):,} of {len(df_full):,} contacts")
if active_chips:
    c_top2.markdown(" · ".join(active_chips))

# ---- Table ----
display = segments.to_export_df(filtered)
st.dataframe(
    display.drop(columns=["Notes", "Manual Tags", "Created"], errors="ignore"),
    use_container_width=True,
    hide_index=True,
    height=480,
)

# ---- Export buttons ----
st.subheader("⬇️ Download segment")
col_x, col_c, col_l = st.columns(3)
xlsx_bytes = segments.to_excel_bytes(display, sheet_name="Segment")
col_x.download_button(
    "📊 Download as Excel (.xlsx)",
    xlsx_bytes,
    file_name=f"shallwe_segment_{len(display)}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
csv_bytes = display.to_csv(index=False).encode("utf-8")
col_c.download_button("📄 CSV", csv_bytes, file_name=f"shallwe_segment_{len(display)}.csv", mime="text/csv")
emails_only = "\n".join(display["Email"].dropna().astype(str).tolist())
col_l.download_button("✉️ Email list (.txt)", emails_only.encode("utf-8"),
                      file_name=f"shallwe_emails_{len(display)}.txt", mime="text/plain")

st.divider()

# ---- Detail drawer ----
st.subheader("Contact detail")
if filtered.empty:
    st.caption("No contact selected.")
else:
    name_to_id = {f"{r['full_name'] or '(no name)'} · {r['email']}": int(r["id"])
                  for _, r in filtered.iterrows()}
    pick = st.selectbox("Select a contact", list(name_to_id.keys()))
    if pick:
        cid = name_to_id[pick]
        c = db.get_contact(cid)
        att = db.get_attendance_for_contact(cid)
        col_a, col_b = st.columns([2, 3])
        with col_a:
            st.markdown(f"### {c.get('full_name') or '(no name)'}")
            st.markdown(f"**📧** {c['email']}")
            if c.get("linkedin"): st.markdown(f"**🔗** {c['linkedin']}")
            if c.get("phone"): st.markdown(f"**📞** {c['phone']}")
            if c.get("organization"): st.markdown(f"**🏢** {c['organization']}")
            if c.get("role_title"): st.markdown(f"**💼** {c['role_title']}")
            if c.get("professional_category"): st.markdown(f"**🏷️** {c['professional_category']}")
            if c.get("mandarin_speaker"): st.markdown("**🀄** Speaks Mandarin")
            st.markdown(f"**Source:** {c.get('source') or '—'}")

            if c.get("interests"):
                st.markdown("**Interests:** " + " ".join(f"`{t.strip()}`" for t in c["interests"].split(",") if t.strip()))

            with st.expander("Edit notes / manual tags"):
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
        mandarin_in = st.checkbox("Speaks Mandarin")
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
                "mandarin_speaker": 1 if mandarin_in else 0,
                "tags": tags_in, "notes": notes, "source": "manual",
            })
            st.success("Contact created.")
            st.rerun()
