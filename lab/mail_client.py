import smtplib
from email import message_from_string, policy
from email.message import EmailMessage
from email.utils import getaddresses

import requests

import config

DEFAULT_SENDER = f"assistant@{config.INTERNAL_DOMAIN}"


def _is_internal(address):
    return address.lower().endswith("@" + config.INTERNAL_DOMAIN)


def route_server(recipients):
    """Tat ca nguoi nhan noi bo -> hop thu NOI BO; con lai -> hop thu BEN NGOAI."""
    if all(_is_internal(a) for a in recipients):
        return config.INTERNAL_MAIL, "internal"
    return config.EXTERNAL_MAIL, "external"


def _smtp_send(server, msg):
    with smtplib.SMTP(server["smtp_host"], server["smtp_port"], timeout=15) as s:
        s.send_message(msg)


def send_mail(to, subject, body, sender=DEFAULT_SENDER):
    """Gui thu, tu dong dinh tuyen theo ten mien. Tra ve 'internal' hoac 'external'."""
    recipients = [addr for _, addr in getaddresses([to]) if addr]
    if not recipients:
        raise ValueError("Khong co dia chi nguoi nhan hop le")
    server, box = route_server(recipients)
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)
    _smtp_send(server, msg)
    return box


def deliver_to_inbox(sender, subject, text, html=None, to=None):
    """Dua mot thu vao hop thu NOI BO (dung de nap email thuong / email tan cong)."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to or f"me@{config.INTERNAL_DOMAIN}"
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    _smtp_send(config.INTERNAL_MAIL, msg)


def _parse_item(item):
    """Giai ma 1 thu tu MailHog thanh dict de doc."""
    msg = message_from_string(item["Raw"]["Data"], policy=policy.default)
    plain, html = "", ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain" and not plain:
            plain = part.get_content()
        elif ctype == "text/html" and not html:
            html = part.get_content()
    return {
        "id": item["ID"],
        "from": str(msg["From"] or ""),
        "to": str(msg["To"] or ""),
        "subject": str(msg["Subject"] or ""),
        "body": plain,
        "html": html,
        "date": str(msg["Date"] or ""),
    }


def list_messages(server):
    """Tat ca thu trong mot hop thu, MOI NHAT dung dau."""
    out, start = [], 0
    while True:
        r = requests.get(server["api"] + "/api/v2/messages",
                         params={"start": start, "limit": 50}, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data["items"]
        out.extend(_parse_item(i) for i in items)
        start += len(items)
        if not items or start >= data["total"]:
            break
    return out


def latest_message(server=None):
    """Thu moi nhat (mac dinh o hop thu noi bo), None neu trong."""
    msgs = list_messages(server or config.INTERNAL_MAIL)
    return msgs[0] if msgs else None


def clear_mailbox(server):
    requests.delete(server["api"] + "/api/v1/messages", timeout=10).raise_for_status()