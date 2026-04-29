"""Email templates manager."""
from __future__ import annotations
import streamlit as st

import db

st.set_page_config(page_title="Templates · ShallWe CRM", page_icon="📄", layout="wide")
db.init_db()

st.title("📄 Email Templates")
st.caption("Reusable email templates with {{variable}} substitution.")

templates = db.list_templates()
st.subheader(f"{len(templates)} templates")

for t in templates:
    with st.expander(f"📄 {t['name']}"):
        with st.form(f"edit_{t['id']}"):
            name = st.text_input("Name", value=t["name"], key=f"n_{t['id']}")
            subject = st.text_input("Subject", value=t["subject"] or "", key=f"s_{t['id']}")
            body = st.text_area("Body", value=t["body"] or "", height=280, key=f"b_{t['id']}")
            c1, c2 = st.columns([1, 1])
            if c1.form_submit_button("💾 Save"):
                db.save_template(name, subject, body, template_id=t["id"])
                st.success("Saved.")
                st.rerun()
            if c2.form_submit_button("🗑️ Delete"):
                db.delete_template(t["id"])
                st.warning("Deleted.")
                st.rerun()

st.divider()
st.subheader("➕ New template")
with st.form("new_tpl"):
    name = st.text_input("Name *")
    subject = st.text_input("Subject")
    body = st.text_area("Body", height=240,
                        help="Use {{first_name}}, {{organization}}, etc. for personalization.")
    if st.form_submit_button("Create"):
        if name:
            db.save_template(name, subject, body)
            st.success("Created.")
            st.rerun()
