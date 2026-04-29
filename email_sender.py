"""SMTP email sender. Reads creds from db settings (set on Settings page).

Supports Gmail (smtp.gmail.com:587, App Password) and any other SMTP server.
"""
from __future__ import annotations
import smtplib
import ssl
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

import db


def render(template: str, contact: dict, extra: dict | None = None) -> str:
    """Replace {{var}} placeholders. Falls back to '' if missing."""
    ctx = dict(contact) if contact else {}
    if extra:
        ctx.update(extra)
    if not ctx.get("first_name") and ctx.get("full_name"):
        ctx["first_name"] = str(ctx["full_name"]).split()[0]

    def sub(m):
        key = m.group(1).strip()
        v = ctx.get(key)
        return str(v) if v not in (None, "") else ""

    return re.sub(r"\{\{\s*([\w_]+)\s*\}\}", sub, template or "")


def get_smtp_config() -> dict:
    return {
        "host": db.get_setting("smtp_host", "smtp.gmail.com"),
        "port": int(db.get_setting("smtp_port", "587") or 587),
        "username": db.get_setting("smtp_username", ""),
        "password": db.get_setting("smtp_password", ""),
        "from_email": db.get_setting("smtp_from_email", ""),
        "from_name": db.get_setting("smtp_from_name", "ShallWe Tech"),
        "use_tls": db.get_setting("smtp_use_tls", "1") == "1",
    }


def _connect(cfg: dict):
    ctx = ssl.create_default_context()
    server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=20)
    server.ehlo()
    if cfg["use_tls"]:
        server.starttls(context=ctx)
        server.ehlo()
    if cfg["username"] and cfg["password"]:
        server.login(cfg["username"], cfg["password"])
    return server


def send_email(to_email: str, subject: str, body: str, contact_id: int | None = None,
               cfg: dict | None = None, html: bool = False, server=None) -> tuple[bool, str]:
    """Send a single email. Pass `server` to reuse one SMTP connection across many sends."""
    cfg = cfg or get_smtp_config()
    if not cfg["from_email"] or not cfg["host"]:
        msg = "SMTP not configured. Go to Settings to set host/from/credentials."
        db.log_email(contact_id, to_email, subject, body, "error", msg)
        return False, msg

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg["from_name"], cfg["from_email"]))
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))

    own_server = False
    try:
        if server is None:
            server = _connect(cfg)
            own_server = True
        server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        db.log_email(contact_id, to_email, subject, body, "sent")
        return True, "ok"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        db.log_email(contact_id, to_email, subject, body, "error", err)
        return False, err
    finally:
        if own_server and server is not None:
            try:
                server.quit()
            except Exception:
                pass


def send_bulk(contacts: list[dict], subject_tpl: str, body_tpl: str, html: bool = False,
              extra_ctx: dict | None = None) -> dict:
    cfg = get_smtp_config()
    sent = 0
    failed = 0
    errors = []
    server = None
    try:
        if cfg["from_email"] and cfg["host"]:
            server = _connect(cfg)
        for c in contacts:
            subj = render(subject_tpl, c, extra_ctx)
            body = render(body_tpl, c, extra_ctx)
            ok, err = send_email(
                c["email"], subj, body,
                contact_id=c.get("id"), cfg=cfg, html=html, server=server,
            )
            if ok:
                sent += 1
            else:
                failed += 1
                errors.append((c["email"], err))
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
    return {"sent": sent, "failed": failed, "errors": errors}
