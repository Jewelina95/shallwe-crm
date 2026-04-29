"""ShallWe Tech CRM - Home / Dashboard.

Run: streamlit run app.py
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px

import db

st.set_page_config(
    page_title="ShallWe Tech CRM",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

st.title("ShallWe Tech — Audience CRM")
st.caption("Crafting the future of AI communities · 用户管理与画像分析")

s = db.stats()
events = db.list_events()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Contacts", f"{s['contacts']:,}")
col2.metric("Events", f"{s['events']:,}")
col3.metric("Total Registrations", f"{s['attendance']:,}")
col4.metric("Mandarin Speakers", f"{s['mandarin']:,}")

st.divider()

# Recent activity: top organizations + latest contacts
left, right = st.columns([1, 1])

with left:
    st.subheader("Top Organizations")
    rows = db.list_contacts()
    if rows:
        df = pd.DataFrame(rows)
        org = df["organization"].dropna().str.strip().replace("", pd.NA).dropna()
        if len(org):
            top = org.value_counts().head(15).reset_index()
            top.columns = ["Organization", "Members"]
            fig = px.bar(top, x="Members", y="Organization", orientation="h", height=420)
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No organization data yet.")
    else:
        st.info("No contacts yet. Go to Settings to import your Luma xlsx.")

with right:
    st.subheader("Events")
    if events:
        ev_df = pd.DataFrame(events)[["name", "date", "description"]]
        st.dataframe(ev_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events. They will be created automatically when you import the xlsx.")

st.divider()

st.subheader("Quick Actions")
qa1, qa2, qa3, qa4 = st.columns(4)
qa1.page_link("pages/1_Contacts.py", label="Browse Contacts", icon="👥")
qa2.page_link("pages/2_Analytics.py", label="Audience Analytics", icon="📊")
qa3.page_link("pages/3_Email.py", label="Send Email", icon="✉️")
qa4.page_link("pages/5_Settings.py", label="Settings & Import", icon="⚙️")

with st.expander("First-time setup"):
    st.markdown("""
1. Go to **Settings → Import** to load your `ShallWe Tech - Pat Attendance List.xlsx` (one click).
2. Go to **Settings → SMTP** to set Gmail/Outlook credentials (Gmail needs an *App Password*).
3. Go to **Email** to compose and one-click broadcast to a segment (e.g., Mandarin speakers, Luma Forum attendees).
4. Go to **Analytics** to view audience portrait charts.
""")
