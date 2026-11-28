import html
import json
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
    """Khoa bat dau bang '_' la metadata cho core/nhat ky, core go ra truoc khi dua cho LLM."""
    msg = mail_client.latest_message()
    if msg is None:
        return {"error": "inbox is empty"}
    raw = msg["html"] if msg["html"] else msg["body"]
    meta = {}
    if config.ENABLE_L1:
        from guardrails.sanitize import count_hidden, sanitize, spotlight
        body = spotlight(sanitize(raw))
        meta["_l1"] = {"hidden_removed": count_hidden(raw), "html": bool(msg["html"])}
    else:
        body = _html_to_text(raw) if msg["html"] else raw
    return {"from": msg["from"], "subject": msg["subject"], "body": body[:MAX_BODY], **meta}


def query_db(sql):
    # Mo che do CHI DOC la bien phap an toan cho lab (khong cho model xoa du lieu).
    uri = config.DB_PATH.resolve().as_uri() + "?mode=ro"
    try:
        from guardrails.policy import analyze_sql
        info = analyze_sql(sql)
        tables = sorted(info["tables"])

        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(sql).fetchmany(MAX_ROWS)]
        con.close()

        # Phong thu Second-Order Injection: du lieu tu bang customers (do nguoi ngoai nhap)
        # cung duoc lam sach va gan nhan ranh gioi khi L1 bat.
        if config.ENABLE_L1 and "customers" in info["tables"]:
            from guardrails.sanitize import sanitize, spotlight
            for r in rows:
                for k, v in list(r.items()):
                    if isinstance(v, str) and len(v) > 15 and "@" not in v:
                        r[k] = spotlight(sanitize(v))

        if tables:
            return {"rows": rows, "_tables": tables}
        return rows
    except Exception as e:
        return {"error": str(e)}


def send_email(to, subject, body):
    try:
        mail_client.send_mail(to, subject, body)
        return f"Email sent to {to}"
    except Exception as e:
        return {"error": str(e)}


TOOLS = {"read_email": read_email, "query_db": query_db, "send_email": send_email}


# ------------------------------------------------------- chuan hoa tham so
TOOL_PARAMS = {
    "read_email": {"required": (), "optional": ()},
    "query_db": {"required": ("sql",), "optional": ()},
    "send_email": {"required": ("to", "subject", "body"), "optional": ()},
}
ARG_ALIASES = {
    "query_db": {"query": "sql", "sql_query": "sql", "statement": "sql", "q": "sql"},
    "send_email": {"recipient": "to", "recipients": "to", "email": "to", "to_email": "to",
                   "to_address": "to", "address": "to",
                   "content": "body", "text": "body", "message": "body", "msg": "body",
                   "title": "subject", "subj": "subject"},
}
WRAPPER_KEYS = ("args", "arguments", "parameters", "params", "input", "kwargs")
MAX_UNWRAP = 3


class ToolArgsError(ValueError):
    pass


def normalize_tool_args(tool_name, args):
    if tool_name not in TOOL_PARAMS:
        raise ToolArgsError(f"unknown tool {tool_name!r}")
    notes = []
    if args is None:
        args = {}
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
            notes.append("args la chuoi JSON")
        except ValueError:
            raise ToolArgsError("args must be a JSON object")
    for _ in range(MAX_UNWRAP):
        if (isinstance(args, dict) and len(args) == 1
                and str(next(iter(args))).strip().lower() in WRAPPER_KEYS
                and isinstance(next(iter(args.values())), (dict, type(None)))):
            notes.append(f"mo boc '{next(iter(args))}'")
            args = next(iter(args.values())) or {}
        else:
            break
    if not isinstance(args, dict):
        raise ToolArgsError("args must be a JSON object")

    spec, aliases = TOOL_PARAMS[tool_name], ARG_ALIASES.get(tool_name, {})
    allowed = spec["required"] + spec["optional"]
    out = {}
    for k, v in args.items():
        key = str(k).strip().lower()
        canon = aliases.get(key, key)
        if canon not in allowed:
            raise ToolArgsError(f"unexpected argument {k!r} for {tool_name}; "
                                f"allowed: {', '.join(allowed) or 'none'}")
        if canon == "to" and isinstance(v, (list, tuple)):
            if not all(isinstance(x, str) for x in v):
                raise ToolArgsError("'to' must be a string or a list of strings")
            v = ", ".join(x.strip() for x in v)
            notes.append("'to' dang danh sach")
        elif isinstance(v, bool) or isinstance(v, (dict, list, tuple)) or v is None:
            raise ToolArgsError(f"argument {k!r} must be a string")
        elif isinstance(v, (int, float)):
            v = str(v)
        if canon in out and out[canon] != v:
            raise ToolArgsError(f"conflicting values for {canon!r} (alias {k!r})")
        if canon != k:
            notes.append(f"{k} -> {canon}")
        out[canon] = v
    missing = [r for r in spec["required"] if r not in out]
    if missing:
        raise ToolArgsError(f"missing argument(s) for {tool_name}: {', '.join(missing)}")
    return out, notes