"""Email - one-click broadcast with multi-dimensional segment targeting."""
from __future__ import annotations
import streamlit as st
import pandas as pd

import db
import email_sender as mailer
import segments

st.set_page_config(page_title="Email · ShallWe CRM", page_icon="✉️", layout="wide")
db.init_db()

st.title("✉️ Email Broadcast")
st.caption("Pick a segment by interest / profession / event / language → render template → preview → one-click send.")

df_full = segments.enriched_contacts()
if df_full.empty:
    st.warning("No contacts. Go to **Settings → Import** first.")
    st.stop()

# ===== 1. Segment =====
st.subheader("1. Build the segment")

all_interests = db.all_interest_tags()
all_pros = sorted(x for x in df_full["professional_category"].unique() if x)
all_orgs = sorted(x for x in df_full["organization"].unique() if x)
all_sources = sorted(x for x in df_full["source"].unique() if x)
events = db.list_events()
event_options = {e["name"]: e["id"] for e in events}

c1, c2, c3 = st.columns(3)
with c1:
    interest_tags = st.multiselect("Interests (any of)", all_interests)
    pro_cats = st.multiselect("Professional category", all_pros)
with c2:
    pick_events = st.multiselect("Attended event", list(event_options.keys()))
    pick_orgs = st.multiselect("Organization", all_orgs)
with c3:
    mandarin = st.radio("Language", ["Any", "Mandarin only", "Non-Mandarin only"], horizontal=False)
    pick_sources = st.multiselect("Source / channel", all_sources)

c4, c5, c6 = st.columns(3)
has_linkedin = c4.checkbox("Has LinkedIn URL")
min_events = c5.slider("Min events attended", 0, max(int(df_full["events_attended"].max() or 0), 1), 0)
approval = c6.selectbox("Approval status", ["", "approved", "declined", "waitlist", "pending"])

filters = {
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
seg = segments.apply_filters(df_full, filters)
recipients = seg[seg["email"].fillna("").str.strip() != ""].to_dict("records")

st.info(f"📬 **{len(recipients)} recipients** match this segment.")
if recipients:
    with st.expander("Preview recipient list"):
        st.dataframe(
            segments.to_export_df(seg)[["Name", "Email", "Professional Category", "Organization", "Interests", "Events Attended"]],
            use_container_width=True, hide_index=True,
        )
    # Allow downloading the targeted list before sending
    xlsx_bytes = segments.to_excel_bytes(segments.to_export_df(seg), sheet_name="Recipients")
    st.download_button(
        "⬇️ Download segment as Excel",
        xlsx_bytes,
        file_name=f"recipients_{len(recipients)}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# ===== 2. Compose =====
st.subheader("2. Compose")
templates = db.list_templates()
tpl_lookup = {"(blank)": None, **{f"📄 {t['name']}": t["id"] for t in templates}}
tpl_pick = st.selectbox("Start from template", list(tpl_lookup.keys()))
init_subject, init_body = "", ""
if tpl_lookup[tpl_pick]:
    t = next(t for t in templates if t["id"] == tpl_lookup[tpl_pick])
    init_subject, init_body = t["subject"], t["body"]

subject = st.text_input("Subject", value=init_subject)
body = st.text_area("Body", value=init_body, height=260,
                    help="Use {{first_name}}, {{full_name}}, {{organization}}, {{role_title}}, etc.")
html_mode = st.checkbox("Send as HTML")

st.markdown("**Variables:** `{{first_name}}` `{{full_name}}` `{{email}}` `{{organization}}` `{{role_title}}` `{{professional_category}}` `{{interests}}`")

# ===== 3. Preview =====
if recipients:
    st.subheader("3. Preview (first recipient)")
    preview = recipients[0]
    pcol1, pcol2 = st.columns(2)
    pcol1.markdown(f"**To:** {preview.get('full_name')} <{preview['email']}>")
    pcol1.markdown(f"**Subject:** {mailer.render(subject, preview)}")
    pcol2.code(mailer.render(body, preview), language="markdown")

st.divider()

# ===== 4. Send =====
st.subheader("4. Send")
cfg = mailer.get_smtp_config()
if not cfg["from_email"] or not cfg["host"]:
    st.error("⚠️ SMTP not configured. Go to **Settings** to set credentials before sending.")

confirm = st.checkbox(f"Confirm I want to email **{len(recipients)}** people")
btn_col1, btn_col2 = st.columns([1, 4])
test_mode = btn_col2.checkbox("Test mode — only send to first recipient")

if btn_col1.button("🚀 Send now", type="primary",
                   disabled=not confirm or not subject or not body or not recipients):
    targets = recipients[:1] if test_mode else recipients
    with st.spinner(f"Sending to {len(targets)}…"):
        result = mailer.send_bulk(targets, subject, body, html=html_mode)
    if result["sent"]:
        st.success(f"✅ Sent {result['sent']} emails.")
    if result["failed"]:
        st.error(f"❌ {result['failed']} failed.")
        with st.expander("Errors"):
            for e, msg in result["errors"]:
                st.write(f"- `{e}` — {msg}")

st.divider()

# ===== Log =====
st.subheader("Recent send log")
log = db.list_email_log(100)
if log:
    log_df = pd.DataFrame(log)[["sent_at", "to_email", "subject", "status", "error"]]
    st.dataframe(log_df, use_container_width=True, hide_index=True, height=300)
else:
    st.caption("No emails sent yet.")
