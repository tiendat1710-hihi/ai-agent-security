import html
import re
import sqlite3

import config
from lab import mail_client

MAX_BODY = 3000   # cat bot de khong tran ngu canh 4096 token
MAX_ROWS = 50


def _html_to_text(raw):
    """Bo the HTML kieu don gian (noi dung an kieu display:none van con)."""
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def read_email():
    msg = mail_client.latest_message()
    if msg is None:
        return {"error": "inbox is empty"}
    body = _html_to_text(msg["html"]) if msg["html"] else msg["body"]
    return {"from": msg["from"], "subject": msg["subject"], "body": body[:MAX_BODY]}


def query_db(sql):
    # Mo che do CHI DOC la bien phap an toan cho lab (khong cho model xoa du lieu).
    # Day KHONG phai phong thu du lieu mat: baseline van doc duoc moi cot.
    uri = config.DB_PATH.resolve().as_uri() + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        rows = con.execute(sql).fetchmany(MAX_ROWS)
        con.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def send_email(to, subject, body):
    try:
        mail_client.send_mail(to, subject, body)
        return f"Email sent to {to}"
    except Exception as e:
        return {"error": str(e)}


TOOLS = {"read_email": read_email, "query_db": query_db, "send_email": send_email}