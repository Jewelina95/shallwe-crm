"""Auto Lists - one-click presets and auto-generated tables grouped by any dimension."""
from __future__ import annotations
import re
from io import BytesIO

import pandas as pd
import streamlit as st

import db
import segments

st.set_page_config(page_title="Auto Lists · ShallWe CRM", page_icon="📋", layout="wide")
db.init_db()

st.title("📋 Auto Lists")
st.caption("一键预设 + 按维度自动分组生成多张表，每张表都可独立下载。")

df = segments.enriched_contacts()
if df.empty:
    st.warning("No contacts. Go to **Settings → Import** first.")
    st.stop()

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _has_tag(interests: str, tag: str) -> bool:
    if not interests:
        return False
    return tag in [t.strip() for t in interests.split(",")]


def _split_by_tag(frame: pd.DataFrame, tag: str) -> pd.DataFrame:
    return frame[frame["interests"].fillna("").apply(lambda s: _has_tag(s, tag))]


def _split_by_event_name(frame: pd.DataFrame, event_name: str) -> pd.DataFrame:
    pat = re.escape(event_name)
    return frame[frame["event_names"].fillna("").str.contains(pat, regex=True, na=False)]


def _slug(label: str) -> str:
    return ("".join(c if c.isalnum() else "_" for c in label).strip("_") or "group")[:40]


tab_preset, tab_group, tab_workbook = st.tabs(
    ["⭐ Quick presets", "🧩 Group by dimension", "📚 All-in-one workbook"]
)

# ============================================================
# 1. Quick presets
# ============================================================
with tab_preset:
    st.subheader("Pre-built audience segments")
    st.caption("Ready-to-use lists for common outreach scenarios. Click download to grab xlsx.")

    PRESETS = [
        ("🔥 Most engaged (≥2 events)",
         {"min_events_attended": 2}, "highly_engaged"),
        ("🀄 Mandarin speakers",
         {"mandarin_only": True}, "mandarin"),
        ("🌍 Non-Mandarin (English-first)",
         {"non_mandarin_only": True}, "non_mandarin"),
        ("🚀 Founders & Startups",
         {"interest_tags": ["Founder / Startup"]}, "founders"),
        ("💰 Investors / VCs",
         {"interest_tags": ["Investor / VC"]}, "investors"),
        ("🎓 Academic Researchers",
         {"professional_categories": ["Academic Researcher"]}, "academics"),
        ("🏢 Enterprise Professionals",
         {"professional_categories": ["Enterprise Professional"]}, "enterprise"),
        ("🤖 LLM / Agent enthusiasts",
         {"interest_tags": ["LLM", "Agent"]}, "llm_agent"),
        ("🌐 World Model crowd",
         {"interest_tags": ["World Model", "Multimodal", "Computer Vision"]}, "world_model"),
        ("🦾 Robotics / Embodied AI",
         {"interest_tags": ["Robotics / Embodied AI", "RL"]}, "robotics"),
        ("📈 FinTech / Quant",
         {"interest_tags": ["FinTech / Quant"]}, "fintech"),
        ("🩺 Healthcare AI",
         {"interest_tags": ["Healthcare AI"]}, "healthcare"),
        ("🎨 Architecture / Design AI",
         {"interest_tags": ["Architecture / Design"]}, "architecture"),
        ("💻 Vibe Coding workshop alumni",
         {"interest_tags": ["Vibe Coding"]}, "vibe_coding"),
        ("🔗 Has LinkedIn (best for outreach)",
         {"has_linkedin": True}, "with_linkedin"),
        ("✅ Approved attendees only",
         {"approval_status": "approved"}, "approved"),
        ("🎯 Mandarin Founders (top conversion)",
         {"mandarin_only": True, "interest_tags": ["Founder / Startup"]}, "mandarin_founders"),
        ("🎯 Mandarin Academic Researchers",
         {"mandarin_only": True, "professional_categories": ["Academic Researcher"]}, "mandarin_academics"),
    ]

    cols = st.columns(3)
    for i, (label, flt, slug) in enumerate(PRESETS):
        with cols[i % 3]:
            sub = segments.apply_filters(df, flt)
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(f"{len(sub):,} contacts")
                if len(sub) > 0:
                    export = segments.to_export_df(sub)
                    xlsx = segments.to_excel_bytes(export, sheet_name=slug[:30])
                    st.download_button(
                        "📥 Download xlsx",
                        xlsx,
                        file_name=f"shallwe_{slug}_{len(sub)}.xlsx",
                        mime=XLSX_MIME,
                        key=f"preset_{slug}",
                        use_container_width=True,
                    )
                else:
                    st.caption("(empty — no matches)")

# ============================================================
# 2. Group by dimension
# ============================================================
with tab_group:
    st.subheader("Auto-split into groups")
    st.caption("Pick a column. Each unique value becomes a separate table with its own download.")

    dimension = st.selectbox(
        "Group by",
        [
            "Interest tag",
            "Professional category",
            "Organization (top 30)",
            "Event attended",
            "Source / channel",
            "Engagement level",
            "Mandarin / Non-Mandarin",
            "Approval status",
        ],
    )

    min_size = st.slider("Hide groups smaller than", 1, 50, 1)
    groups: list[tuple[str, pd.DataFrame]] = []

    if dimension == "Interest tag":
        for tag in db.all_interest_tags():
            sub = _split_by_tag(df, tag)
            if len(sub) >= min_size:
                groups.append((tag, sub))
    elif dimension == "Professional category":
        for cat, sub in df.groupby("professional_category"):
            if cat and len(sub) >= min_size:
                groups.append((cat, sub))
    elif dimension == "Organization (top 30)":
        top_orgs = df["organization"].value_counts().head(30).index.tolist()
        for org in top_orgs:
            sub = df[df["organization"] == org]
            if org and len(sub) >= min_size:
                groups.append((org, sub))
    elif dimension == "Event attended":
        for ev in db.list_events():
            sub = _split_by_event_name(df, ev["name"])
            if len(sub) >= min_size:
                groups.append((ev["name"], sub))
    elif dimension == "Source / channel":
        for src, sub in df.groupby("source"):
            label = src or "(unknown)"
            if len(sub) >= min_size:
                groups.append((label, sub))
    elif dimension == "Engagement level":
        for label, sub in [
            ("0 events (subscribed only)", df[df["events_attended"] == 0]),
            ("1 event", df[df["events_attended"] == 1]),
            ("2 events", df[df["events_attended"] == 2]),
            ("3+ events (super-fans)", df[df["events_attended"] >= 3]),
        ]:
            if len(sub) >= min_size:
                groups.append((label, sub))
    elif dimension == "Mandarin / Non-Mandarin":
        groups.append(("Mandarin speakers", df[df["mandarin_speaker"] == 1]))
        groups.append(("Non-Mandarin", df[df["mandarin_speaker"] == 0]))
    elif dimension == "Approval status":
        for status in ["approved", "declined", "waitlist", "pending"]:
            sub = df[df["approval_statuses"].fillna("").str.contains(status, case=False, na=False)]
            if len(sub) >= min_size:
                groups.append((status, sub))

    if not groups:
        st.info("No groups match — lower the size threshold or pick another dimension.")
    else:
        st.success(
            f"Generated **{len(groups)} tables** — total **{sum(len(g[1]) for g in groups):,} contacts** "
            "(rows can overlap when grouped by interest)."
        )

        groups.sort(key=lambda g: -len(g[1]))

        for label, sub in groups:
            slug = _slug(label)
            with st.expander(f"📂 **{label}** — {len(sub):,} contacts", expanded=False):
                export = segments.to_export_df(sub)
                st.dataframe(
                    export[["Name", "Email", "Professional Category", "Organization", "Interests", "Events Attended"]],
                    use_container_width=True, hide_index=True, height=240,
                )
                xlsx = segments.to_excel_bytes(export, sheet_name=slug[:30])
                c1, c2 = st.columns(2)
                c1.download_button(
                    "📊 Download this group (xlsx)",
                    xlsx,
                    file_name=f"shallwe_{slug}_{len(sub)}.xlsx",
                    mime=XLSX_MIME,
                    key=f"grp_{slug}",
                )
                emails = "\n".join(export["Email"].dropna().astype(str).tolist())
                c2.download_button(
                    "✉️ Email list (.txt)",
                    emails.encode("utf-8"),
                    file_name=f"shallwe_{slug}_emails.txt",
                    mime="text/plain",
                    key=f"grpmail_{slug}",
                )

# ============================================================
# 3. All-in-one workbook
# ============================================================
with tab_workbook:
    st.subheader("Build a multi-sheet Excel workbook")
    st.caption("Pick a dimension. Generates ONE xlsx with one sheet per group — perfect for forwarding to a collaborator.")

    wb_dim = st.selectbox(
        "Group by",
        ["Interest tag", "Professional category", "Event attended", "Engagement level", "Source / channel"],
        key="wb_dim",
    )
    wb_min = st.slider("Skip groups smaller than", 1, 50, 3, key="wb_min")

    if st.button("📚 Generate workbook", type="primary"):
        wb_groups: list[tuple[str, pd.DataFrame]] = []
        if wb_dim == "Interest tag":
            for tag in db.all_interest_tags():
                sub = _split_by_tag(df, tag)
                if len(sub) >= wb_min:
                    wb_groups.append((tag, sub))
        elif wb_dim == "Professional category":
            for cat, sub in df.groupby("professional_category"):
                if cat and len(sub) >= wb_min:
                    wb_groups.append((cat, sub))
        elif wb_dim == "Event attended":
            for ev in db.list_events():
                sub = _split_by_event_name(df, ev["name"])
                if len(sub) >= wb_min:
                    wb_groups.append((ev["name"], sub))
        elif wb_dim == "Engagement level":
            for label, sub in [
                ("0 events", df[df["events_attended"] == 0]),
                ("1 event", df[df["events_attended"] == 1]),
                ("2 events", df[df["events_attended"] == 2]),
                ("3+ events", df[df["events_attended"] >= 3]),
            ]:
                if len(sub) >= wb_min:
                    wb_groups.append((label, sub))
        elif wb_dim == "Source / channel":
            for src, sub in df.groupby("source"):
                if src and len(sub) >= wb_min:
                    wb_groups.append((src, sub))

        if not wb_groups:
            st.warning("No groups match.")
        else:
            wb_groups.sort(key=lambda g: -len(g[1]))
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                summary = pd.DataFrame([(g[0], len(g[1])) for g in wb_groups], columns=["Group", "Contacts"])
                summary.to_excel(writer, sheet_name="_Summary", index=False)
                ws = writer.sheets["_Summary"]
                ws.column_dimensions["A"].width = 40
                ws.column_dimensions["B"].width = 12

                used_names = {"_Summary"}
                for label, sub in wb_groups:
                    sheet = _slug(label)[:30] or "sheet"
                    base = sheet
                    n = 2
                    while sheet in used_names:
                        sheet = f"{base[:27]}_{n}"
                        n += 1
                    used_names.add(sheet)
                    segments.to_export_df(sub).to_excel(writer, sheet_name=sheet, index=False)

            st.success(f"Workbook with {len(wb_groups)} sheets ready ({sum(len(g[1]) for g in wb_groups):,} rows).")
            st.download_button(
                "⬇️ Download workbook",
                buf.getvalue(),
                file_name=f"shallwe_grouped_by_{wb_dim.replace(' ', '_').lower()}.xlsx",
                mime=XLSX_MIME,
                type="primary",
            )
