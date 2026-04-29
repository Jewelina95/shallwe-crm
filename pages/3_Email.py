"""Email - one-click broadcast with templates and variable substitution."""
from __future__ import annotations
import streamlit as st
import pandas as pd

import db
import email_sender as mailer

st.set_page_config(page_title="Email · ShallWe CRM", page_icon="✉️", layout="wide")
db.init_db()

st.title("✉️ Email Broadcast")
st.caption("Pick a segment, pick or write a template, preview, send.")

# Build segment
st.subheader("1. Choose recipients")
events = db.list_events()
event_lookup = {"All contacts": None, **{f"Event: {e['name']}": e["id"] for e in events}}

c1, c2, c3 = st.columns(3)
seg = c1.selectbox("Segment", list(event_lookup.keys()))
contacts_all = db.list_contacts()
df_all = pd.DataFrame(contacts_all) if contacts_all else pd.DataFrame()
pro_options = ["All categories"] + sorted(
    [x for x in (df_all.get("professional_category", pd.Series()).dropna().unique() if not df_all.empty else []) if x]
)
pro = c2.selectbox("Professional category", pro_options)
mandarin = c3.selectbox("Language", ["Any", "Mandarin only", "Non-Mandarin only"])

filters = {
    "event_id": event_lookup[seg],
    "professional_category": None if pro == "All categories" else pro,
    "mandarin_only": mandarin == "Mandarin only",
}
recipients = db.list_contacts(filters)
if mandarin == "Non-Mandarin only":
    recipients = [r for r in recipients if not r.get("mandarin_speaker")]
recipients = [r for r in recipients if (r.get("email") or "").strip()]

st.info(f"**{len(recipients)} recipients** match this segment.")
if recipients:
    with st.expander("Preview recipient list"):
        st.dataframe(
            pd.DataFrame(recipients)[["full_name", "email", "professional_category", "organization"]],
            use_container_width=True, hide_index=True,
        )

st.divider()

# Template
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

st.markdown("**Available variables:** `{{first_name}}` `{{full_name}}` `{{email}}` `{{organization}}` `{{role_title}}` `{{professional_category}}`")

# Preview
if recipients:
    st.subheader("3. Preview (first recipient)")
    preview = recipients[0]
    pcol1, pcol2 = st.columns(2)
    pcol1.markdown(f"**To:** {preview.get('full_name')} <{preview['email']}>")
    pcol1.markdown(f"**Subject:** {mailer.render(subject, preview)}")
    pcol2.code(mailer.render(body, preview), language="markdown")

st.divider()

# Send
st.subheader("4. Send")
cfg = mailer.get_smtp_config()
if not cfg["from_email"] or not cfg["host"]:
    st.error("⚠️ SMTP not configured. Go to **Settings** to set credentials before sending.")

confirm = st.checkbox(f"Confirm I want to email **{len(recipients)}** people")
btn_col1, btn_col2 = st.columns([1, 4])
test_mode = btn_col2.checkbox("Test mode — only send to first recipient")

if btn_col1.button("🚀 Send now", type="primary", disabled=not confirm or not subject or not body or not recipients):
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

# Log
st.subheader("Recent send log")
log = db.list_email_log(100)
if log:
    log_df = pd.DataFrame(log)[["sent_at", "to_email", "subject", "status", "error"]]
    st.dataframe(log_df, use_container_width=True, hide_index=True, height=300)
else:
    st.caption("No emails sent yet.")
