"""Settings - SMTP config + xlsx import."""
from __future__ import annotations
from pathlib import Path

import streamlit as st

import db
from import_excel import import_xlsx

st.set_page_config(page_title="Settings · ShallWe CRM", page_icon="⚙️", layout="wide")
db.init_db()

st.title("⚙️ Settings")

tab1, tab2, tab3 = st.tabs(["📥 Import", "📧 SMTP", "🧹 Database"])

# -------- 1. Import --------
with tab1:
    st.subheader("Import Luma attendance xlsx")
    st.caption(
        "Loads sheets `Luma List`, `Tare`, `Non-Luma List` from your Pat Attendance file. "
        "Idempotent — running again will update existing contacts and skip duplicates."
    )

    default_path = "/Users/wenshaoyue/Desktop/shallwetech/ShallWe Tech - Pat Attendance List.xlsx"
    path = st.text_input("Path to xlsx", value=default_path)

    c1, c2 = st.columns([1, 4])
    if c1.button("🚀 Import now", type="primary"):
        if not Path(path).exists():
            st.error(f"File not found: {path}")
        else:
            with st.spinner("Importing…"):
                summary = import_xlsx(path)
            st.success("Imported.")
            st.json(summary)
            st.json(db.stats())

    st.divider()
    st.subheader("Or upload another xlsx")
    up = st.file_uploader("Upload xlsx", type=["xlsx"])
    if up is not None:
        tmp = Path("/tmp") / up.name
        tmp.write_bytes(up.read())
        with st.spinner("Importing…"):
            summary = import_xlsx(tmp)
        st.success("Imported.")
        st.json(summary)

# -------- 2. SMTP --------
with tab2:
    st.subheader("SMTP server")
    st.caption(
        "For Gmail: host `smtp.gmail.com`, port `587`, username = your Gmail, "
        "password = a Gmail **App Password** (not your account password). "
        "Generate at https://myaccount.google.com/apppasswords."
    )
    cfg = {
        "host": db.get_setting("smtp_host", "smtp.gmail.com"),
        "port": db.get_setting("smtp_port", "587"),
        "username": db.get_setting("smtp_username", ""),
        "password": db.get_setting("smtp_password", ""),
        "from_email": db.get_setting("smtp_from_email", ""),
        "from_name": db.get_setting("smtp_from_name", "ShallWe Tech"),
        "use_tls": db.get_setting("smtp_use_tls", "1"),
    }
    with st.form("smtp"):
        c1, c2 = st.columns(2)
        host = c1.text_input("SMTP host", value=cfg["host"])
        port = c2.text_input("Port", value=cfg["port"])
        username = c1.text_input("Username", value=cfg["username"])
        password = c2.text_input("Password / App Password", value=cfg["password"], type="password")
        from_email = c1.text_input("From email", value=cfg["from_email"], placeholder="hello@shallwe.tech")
        from_name = c2.text_input("From name", value=cfg["from_name"])
        use_tls = st.checkbox("Use STARTTLS", value=cfg["use_tls"] == "1")
        if st.form_submit_button("💾 Save"):
            db.set_setting("smtp_host", host)
            db.set_setting("smtp_port", port)
            db.set_setting("smtp_username", username)
            db.set_setting("smtp_password", password)
            db.set_setting("smtp_from_email", from_email)
            db.set_setting("smtp_from_name", from_name)
            db.set_setting("smtp_use_tls", "1" if use_tls else "0")
            st.success("Saved. Try sending a test in Email page.")

# -------- 3. Database --------
with tab3:
    st.subheader("Database")
    st.code(str(db.DB_PATH))
    s = db.stats()
    st.json(s)

    st.subheader("Export all contacts")
    import pandas as pd
    rows = db.list_contacts()
    if rows:
        df = pd.DataFrame(rows)
        st.download_button(
            "⬇️ Download contacts CSV",
            df.to_csv(index=False).encode("utf-8"),
            "shallwe_contacts.csv",
            "text/csv",
        )

    st.subheader("⚠️ Danger zone")
    confirm = st.text_input("Type DELETE to wipe the database")
    if st.button("Wipe database", type="secondary", disabled=confirm != "DELETE"):
        db.DB_PATH.unlink(missing_ok=True)
        db.init_db()
        st.warning("Database wiped.")
