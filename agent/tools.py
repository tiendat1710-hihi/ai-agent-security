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


# ------------------------------------------------------- chuan hoa tham so
# Chay TAT DINH truoc policy: policy, checkpoint HITL va tool thuc thi cung nhin
# thay MOT bo tham so da chuan hoa (nguoi duyet thay dung cai se chay).
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
    """Tra ve (args_chuan, ghi_chu). Nem ToolArgsError neu khong chuan hoa duoc.
    1. args la chuoi JSON -> parse.  2. mo boc {"args": {...}} long nhau (<= 3 lop).
    3. khoa: strip + lower, anh xa alias -> ten chuan.  4. alias va ten chuan cung
    co mat ma khac gia tri -> tu choi (mo ho).  5. tham so la -> tu choi.
    6. thieu tham so bat buoc -> tu choi.  7. 'to' dang list -> 'a, b'; gia tri
    phai la chuoi (so -> chuoi), dict/list long -> tu choi."""
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