import html
import re
import sqlite3
from contextlib import closing

import config
from lab import mail_client

MAX_BODY = 3000   # cat bot de khong tran ngu canh 4096 token
MAX_ROWS = 50
SENSITIVE_TABLES = {"salaries", "customers", "api_keys"}


def _db_uri():
    return config.DB_PATH.resolve().as_uri() + "?mode=ro"


def _authorizer(allow_sensitive, sensitive_tables):
    def authorize(action, name, detail, database, source):
        if action == sqlite3.SQLITE_READ:
            table = (name or "").lower()
            if table.startswith(("sqlite_", "pragma_")):
                return sqlite3.SQLITE_DENY
            if table in SENSITIVE_TABLES:
                sensitive_tables.add(table)
                if not allow_sensitive:
                    return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION:
            if (detail or "").lower() in {"load_extension", "readfile", "writefile"}:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return authorize


def inspect_query(sql):
    sensitive_tables = set()
    with closing(sqlite3.connect(_db_uri(), uri=True)) as con:
        con.set_authorizer(_authorizer(True, sensitive_tables))
        con.execute("EXPLAIN " + sql)
    return sensitive_tables


def _html_to_text(raw):
    """Bo the HTML kieu don gian (noi dung an kieu display:none van con)."""
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def read_email(*, enable_l1=None):
    msg = mail_client.latest_message()
    if msg is None:
        return {"error": "inbox is empty"}
    raw = msg["html"] if msg["html"] else msg["body"]
    if enable_l1 is None:
        enable_l1 = config.ENABLE_L1
    if enable_l1:
        from guardrails.sanitize import sanitize, spotlight
        body = spotlight(sanitize(raw))
    else:
        body = _html_to_text(raw) if msg["html"] else raw
    return {"from": msg["from"], "subject": msg["subject"], "body": body[:MAX_BODY]}


def query_db(sql, *, protected=False, allow_sensitive=False):
    # Mo che do CHI DOC la bien phap an toan cho lab (khong cho model xoa du lieu).
    # Day KHONG phai phong thu du lieu mat: baseline van doc duoc moi cot.
    try:
        with closing(sqlite3.connect(_db_uri(), uri=True)) as con:
            if protected:
                con.set_authorizer(_authorizer(allow_sensitive, set()))
            con.row_factory = sqlite3.Row
            rows = con.execute(sql).fetchmany(MAX_ROWS)
            return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


def send_email(to, subject, body):
    try:
        mail_client.send_mail(to, subject, body)
        return f"Email sent to {to}"
    except OSError as error:
        return {"error": str(error), "infra_error": True}
    except Exception as e:
        return {"error": str(e)}


TOOLS = {"read_email": read_email, "query_db": query_db, "send_email": send_email}
