"""Analytics - Audience portrait and engagement metrics."""
from __future__ import annotations
import json
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from keywords import top_interests, extract_interests, INTEREST_TAGS

st.set_page_config(page_title="Analytics · ShallWe CRM", page_icon="📊", layout="wide")
db.init_db()

st.title("📊 Audience Analytics")
st.caption("Portrait of your community — who they are, what they care about, how engaged they are.")

contacts = db.list_contacts()
events = db.list_events()
if not contacts:
    st.warning("No contacts yet. Go to **Settings → Import** first.")
    st.stop()

df = pd.DataFrame(contacts)

# Pull all attendance for cross analysis
with db.get_conn() as conn:
    att_df = pd.read_sql_query(
        "SELECT ea.*, e.name AS event_name, e.date AS event_date "
        "FROM event_attendance ea JOIN events e ON e.id=ea.event_id",
        conn,
    )

# events attended per contact
counts = att_df.groupby("contact_id").size().rename("events_attended") if len(att_df) else pd.Series(dtype=int)
df = df.merge(counts, left_on="id", right_index=True, how="left").fillna({"events_attended": 0})
df["events_attended"] = df["events_attended"].astype(int)

# ===== KPIs =====
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Contacts", f"{len(df):,}")
k2.metric("Events", f"{len(events):,}")
k3.metric("Avg events / contact", f"{df['events_attended'].mean():.2f}")
k4.metric("Multi-event attendees", f"{(df['events_attended'] >= 2).sum():,}")
checkin_rate = (att_df["checked_in_at"].notna() & (att_df["checked_in_at"] != "")).mean() if len(att_df) else 0
k5.metric("Check-in rate", f"{checkin_rate*100:.1f}%")

st.divider()

# ===== Tabs =====
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏷️ Demographics", "🎯 Interests", "📅 Engagement", "🏢 Organizations", "📥 Acquisition"]
)

# -------- 1. Demographics --------
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Professional category")
        s = df["professional_category"].fillna("(unspecified)").value_counts().reset_index()
        s.columns = ["Category", "Count"]
        fig = px.pie(s, names="Category", values="Count", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Mandarin speakers")
        m_counts = df["mandarin_speaker"].fillna(0).astype(int).value_counts().rename(
            index={1: "Mandarin", 0: "Non-Mandarin"}
        ).reset_index()
        m_counts.columns = ["Group", "Count"]
        fig = px.pie(m_counts, names="Group", values="Count", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Top role / job titles")
        r = df["role_title"].dropna().str.strip().replace("", pd.NA).dropna()
        if len(r):
            top = r.value_counts().head(15).reset_index()
            top.columns = ["Role", "Count"]
            fig = px.bar(top, x="Count", y="Role", orientation="h", height=450)
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.subheader("LinkedIn coverage")
        has_linkedin = df["linkedin"].fillna("").astype(str).str.strip().ne("").sum()
        cov = pd.DataFrame({
            "Group": ["Has LinkedIn", "No LinkedIn"],
            "Count": [has_linkedin, len(df) - has_linkedin],
        })
        fig = px.pie(cov, names="Group", values="Count", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

# -------- 2. Interests --------
with tab2:
    st.subheader("AI-domain interests (extracted from registration answers)")
    st.caption(
        "Inferred from open-text fields: motivation, questions for speakers, experience, role, organization."
    )

    # Combine free-text from each contact's attendance + their profile fields
    text_by_contact: dict[int, str] = {}
    for cid, group in att_df.groupby("contact_id"):
        text_by_contact[cid] = " ".join(
            str(v or "") for v in group[["motivation", "questions_for_speakers", "experience"]].values.ravel()
        )
    rows_for_tags = []
    for _, c in df.iterrows():
        blob = (text_by_contact.get(c["id"], "") + " " +
                " ".join(filter(None, [c.get("role_title"), c.get("organization"), c.get("professional_category")])))
        rows_for_tags.append({"id": c["id"], "blob": blob})
    interest_counter: Counter = Counter()
    contact_tags: dict[int, list[str]] = {}
    for r in rows_for_tags:
        tags = extract_interests(r["blob"])
        contact_tags[r["id"]] = tags
        for t in tags:
            interest_counter[t] += 1

    if interest_counter:
        ic = pd.DataFrame(interest_counter.most_common(), columns=["Interest", "Contacts"])
        fig = px.bar(ic, x="Contacts", y="Interest", orientation="h", height=520)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No interests detected. Add free-text answers or extend INTEREST_TAGS in keywords.py.")

    # Word frequency from "What questions you have for our speakers?"
    st.subheader("What does the audience want to ask speakers?")
    qs = att_df["questions_for_speakers"].dropna().astype(str)
    if len(qs):
        text = " ".join(qs).lower()
        words = re.findall(r"[a-zA-Z一-鿿]{3,}", text)
        stop = {"the", "and", "for", "are", "with", "you", "your", "have", "what", "how", "this",
                "that", "from", "will", "can", "any", "our", "would", "like", "more", "about",
                "they", "but", "not", "all", "其实", "他们", "我们", "可以", "什么", "怎么", "如何"}
        wc = Counter(w for w in words if w not in stop)
        top_words = pd.DataFrame(wc.most_common(40), columns=["Word", "Count"])
        fig = px.bar(top_words, x="Count", y="Word", orientation="h", height=600)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No speaker questions captured yet.")

    # Vibe Coding experience (from Tare workshop)
    if "experience" in att_df.columns:
        vc = att_df["experience"].dropna().astype(str).str.strip()
        vibe_levels = vc[vc.str.match(r"^(Daily User|Regular User|New but highly interested|Never used)$", na=False)]
        if len(vibe_levels):
            st.subheader("Vibe Coding experience level (Tare workshop)")
            vl = vibe_levels.value_counts().reset_index()
            vl.columns = ["Level", "Count"]
            fig = px.bar(vl, x="Level", y="Count")
            st.plotly_chart(fig, use_container_width=True)

# -------- 3. Engagement --------
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Events attended per contact")
        ea = df["events_attended"].astype(int)
        bins = ea.apply(lambda n: "0" if n == 0 else ("1" if n == 1 else ("2" if n == 2 else "3+"))).value_counts().reindex(
            ["0", "1", "2", "3+"], fill_value=0
        ).reset_index()
        bins.columns = ["Events", "Contacts"]
        fig = px.bar(bins, x="Events", y="Contacts", color="Events")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Approval status across all registrations")
        if len(att_df):
            ap = att_df["approval_status"].fillna("(none)").value_counts().reset_index()
            ap.columns = ["Status", "Count"]
            fig = px.pie(ap, names="Status", values="Count", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Most engaged contacts")
    top_engage = df.sort_values("events_attended", ascending=False).head(20)[
        ["full_name", "email", "professional_category", "organization", "events_attended"]
    ].rename(columns={
        "full_name": "Name", "email": "Email",
        "professional_category": "Category", "organization": "Organization",
        "events_attended": "Events",
    })
    st.dataframe(top_engage, use_container_width=True, hide_index=True)

    if len(att_df):
        st.subheader("Registrations over time")
        att_df["registered_at"] = pd.to_datetime(att_df["registered_at"], errors="coerce", utc=True)
        ts = att_df.dropna(subset=["registered_at"]).copy()
        if len(ts):
            ts["day"] = ts["registered_at"].dt.date
            daily = ts.groupby(["day", "event_name"]).size().reset_index(name="count")
            fig = px.line(daily, x="day", y="count", color="event_name", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# -------- 4. Organizations --------
with tab4:
    st.subheader("Top organizations")
    org = df["organization"].dropna().str.strip().replace("", pd.NA).dropna()
    if len(org):
        top = org.value_counts().head(25).reset_index()
        top.columns = ["Organization", "Members"]
        fig = px.bar(top, x="Members", y="Organization", orientation="h", height=600)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

        # Diversity indicator
        st.metric("Distinct organizations", f"{org.nunique():,}")
        st.metric("Single-person orgs", f"{(org.value_counts() == 1).sum():,}")

# -------- 5. Acquisition --------
with tab5:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Source / channel")
        src = df["source"].fillna("(unknown)").value_counts().reset_index()
        src.columns = ["Source", "Contacts"]
        fig = px.pie(src, names="Source", values="Contacts", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Cross-event overlap")
        if len(att_df) and att_df["event_name"].nunique() >= 2:
            pivot = att_df.assign(v=1).pivot_table(
                index="contact_id", columns="event_name", values="v", aggfunc="max", fill_value=0
            )
            overlap = pd.DataFrame(
                {"event": pivot.columns,
                 "only_this": [(pivot[c] == 1).sum() - ((pivot[c] == 1) & (pivot.drop(columns=[c]).sum(axis=1) > 0)).sum() for c in pivot.columns],
                 "also_attended_other": [((pivot[c] == 1) & (pivot.drop(columns=[c]).sum(axis=1) > 0)).sum() for c in pivot.columns]}
            )
            fig = px.bar(overlap.melt(id_vars="event", var_name="bucket", value_name="count"),
                         x="event", y="count", color="bucket", barmode="stack")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Need ≥ 2 events for overlap analysis.")
