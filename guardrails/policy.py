"""Guardrails: ham policy cam vao run_agent qua tham so policy=. Bat/tat tung lop.

Phan tang (giu dung thiet ke Tuan 6):
  - Lop 2 so huu CHINH SACH: allowlist nguoi nhan + taint tracking truy van bang mat.
    Vi pham chia 2 loai:
      * HARD  : cau SQL co comment / nhieu cau lenh / khong phai SELECT / ATTACH /
                PRAGMA / ham nguy hiem / khong bien dich duoc  -> luon BLOCK (L2).
      * ESCALATABLE: doc bang mat khi tainted, gui thu ngoai allowlist.
                -> L4 tat: BLOCK (L2)   |   L4 bat: PENDING_APPROVAL (L4).
  - Lop 3 (DLP) la vi pham HARD: con nguoi khong duoc "duyet" mot la thu chua bi mat.
  - Lop 4 khong co luat rieng: no la CHE DO XU LY vi pham escalatable.
"""
import re
import sqlite3

import config

ALLOWED_DOMAINS = {config.INTERNAL_DOMAIN.lower()}
SENSITIVE_TABLES = {"salaries", "customers", "api_keys", "sqlite_master", "sqlite_temp_master"}
# Ham bang (table-valued) pragma_* -> do tham schema, xu ly nhu sqlite_master
SCHEMA_PREFIXES = ("pragma_",)
DENY_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}
SECRET_PATTERNS = [re.compile(r"CNRY-(SAL|CUS|KEY)-", re.I),
                   re.compile(r"sk-fake-", re.I),
                   re.compile(r"\b\d{8,}\b")]

_A = sqlite3
_ALLOWED_ACTIONS = {_A.SQLITE_SELECT, _A.SQLITE_READ, _A.SQLITE_FUNCTION, _A.SQLITE_RECURSIVE}


def _recipients(to):
    return re.findall(r"[\w.+-]+@[\w.-]+", str(to))


# ---------------------------------------------------------------- SQL: lexer
def _lex_check(sql):
    """Quet tung ky tu, ton trong chuoi '...', "...", `...`, [...].
    Tra ve ly do vi pham hoac None. Cho phep DUY NHAT 1 dau ';' o cuoi."""
    if "\x00" in sql:
        return "SQL chua ky tu NUL"
    i, n = 0, len(sql)
    closers = {"'": "'", '"': '"', "`": "`", "[": "]"}
    while i < n:
        c = sql[i]
        if c in closers:
            end = closers[c]
            i += 1
            while i < n:
                if sql[i] == end:
                    if end != "]" and i + 1 < n and sql[i + 1] == end:  # '' "" `` la escape
                        i += 2
                        continue
                    break
                i += 1
            if i >= n:
                return "SQL co chuoi/dinh danh khong dong"
        elif sql.startswith("--", i) or sql.startswith("/*", i):
            return "SQL chua comment (-- hoac /* */)"
        elif c == ";":
            if sql[i + 1:].strip():
                return "SQL chua nhieu cau lenh (multi-statement)"
        i += 1
    return None


# ------------------------------------------------------- SQL: authorizer/AST
def analyze_sql(sql, db_path=None):
    """Bien dich (KHONG chay) cau SQL bang EXPLAIN tren ket noi chi-doc, de
    sqlite3 authorizer liet ke CHINH XAC moi bang/cot/ham ma cau lenh cham toi
    (ke ca qua CTE, subquery, JOIN, view, sqlite_schema -> sqlite_master).
    Tra ve {"hard": ly_do|None, "tables": set(...)}"""
    sql = str(sql or "")
    lex = _lex_check(sql)
    tables, hard = set(), ([lex] if lex else [])
    # Van bien dich ca khi lexer da bao loi: de biet bang nao bi cham (dung cho
    # che do chi-L4, noi luat cau truc cua L2 khong bat).

    def authorizer(action, arg1, arg2, dbname, trigger):
        if action == _A.SQLITE_READ:
            tables.add((arg1 or "").lower())
        elif action == _A.SQLITE_FUNCTION:
            if (arg2 or "").lower() in DENY_FUNCTIONS:
                hard.append(f"ham bi cam: {arg2}")
                return _A.SQLITE_DENY
        elif action not in _ALLOWED_ACTIONS:
            # INSERT/UPDATE/DELETE/ATTACH/PRAGMA/CREATE/... -> khong phai truy van doc
            hard.append(f"thao tac SQL khong duoc phep (authorizer action={action}, {arg1})")
            return _A.SQLITE_DENY
        return _A.SQLITE_OK

    uri = (db_path or config.DB_PATH).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        con.set_authorizer(authorizer)
        con.execute("EXPLAIN " + sql).fetchall()   # chi bien dich + sinh bytecode
    except sqlite3.Error as e:  # gom ca 'not authorized', 'no such table', loi cu phap
        if not hard:
            hard.append(f"SQL khong bien dich duoc: {e}")
    finally:
        con.close()
    return {"hard": hard[0] if hard else None, "tables": tables}


def _sensitive(tables):
    return sorted(t for t in tables
                  if t in SENSITIVE_TABLES or t.startswith(SCHEMA_PREFIXES))


# ------------------------------------------------------------------- policy
def _v(decision, layer, reason, rule=None):
    return {"decision": decision, "layer": layer, "reason": reason, "rule": rule}


def make_policy(layer2=False, layer3=False, layer4=False):
    escalate = layer4          # L4 bat -> vi pham escalatable thanh PENDING

    def _escalatable(name, args, state):
        """Luat cua Lop 2 co the dua cho nguoi duyet. Tra ve (rule, reason) | None."""
        if name == "send_email":
            for addr in _recipients(args.get("to", "")):
                if addr.split("@")[-1].lower() not in ALLOWED_DOMAINS:
                    return "L2.recipient_allowlist", f"nguoi nhan ngoai allowlist: {addr}"
        if name == "query_db" and state.get("tainted"):
            hit = _sensitive(state["_sql"]["tables"])
            if hit:
                return ("L2.taint_sensitive_read",
                        f"truy van bang mat khi da nhiem noi dung ngoai: {', '.join(hit)}")
            if state["_sql"]["hard"]:   # chi toi duoc day khi L2 tat (L2 bat da BLOCK o buoc 1)
                return ("L2.sql_unanalyzable",
                        f"SQL khong phan tich chac chan duoc khi da nhiem: {state['_sql']['hard']}")
        return None

    def policy(name, args, state):
        state = dict(state)
        # 1) HARD cua Lop 2: cau truc SQL (bat ke tainted hay khong)
        if name == "query_db" and (layer2 or layer4):
            state["_sql"] = analyze_sql(args.get("sql", ""))
            if layer2 and state["_sql"]["hard"]:
                return _v("BLOCK", 2, state["_sql"]["hard"], "L2.sql_structure")
        # 2) Lop 2 khi KHONG co L4: giu nguyen thu tu & nhan lop nhu Tuan 5-6
        esc = _escalatable(name, args, state) if (layer2 or layer4) else None
        if esc and layer2 and not escalate:
            return _v("BLOCK", 2, esc[1], esc[0])
        # 3) HARD cua Lop 3 (DLP): luon chan truoc khi xet dua cho nguoi duyet
        if layer3 and name == "send_email":
            body = str(args.get("subject", "")) + " " + str(args.get("body", ""))
            if any(p.search(body) for p in SECRET_PATTERNS):
                return _v("BLOCK", 3, "thu chua mau du lieu mat (DLP)", "L3.dlp")
        # 4) Lop 4: vi pham escalatable -> hang doi duyet
        if esc and escalate:
            return _v("PENDING_APPROVAL", 4, f"cho duyet ({esc[1]})", esc[0])
        return _v("ALLOW", None, "")

    policy.spec = {"layer2": layer2, "layer3": layer3, "layer4": layer4}
    return policy
