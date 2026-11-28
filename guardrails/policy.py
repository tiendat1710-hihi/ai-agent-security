"""Guardrails: ham policy cam vao run_agent qua tham so policy=. Bat/tat tung lop.

Phan tang (giu dung thiet ke Tuan 6 + Nang cap Chuyen gia ATTT):
  - Lop 2 so huu CHINH SACH: allowlist nguoi nhan + taint tracking truy van bang mat.
    Vi pham chia 2 loai:
      * HARD  : cau SQL co comment / nhieu cau lenh / khong phai SELECT / ATTACH /
                PRAGMA / ham nguy hiem / khong bien dich duoc  -> luon BLOCK (L2).
      * ESCALATABLE: doc bang mat khi tainted, gui thu ngoai allowlist.
                -> L4 tat: BLOCK (L2)   |   L4 bat: PENDING_APPROVAL (L4).
  - Lop 3 (DLP) la vi pham HARD: con nguoi khong duoc "duyet" mot la thu chua bi mat,
    bao gom ca du lieu mat da bi ma hoa Base64/Hex/dao nguoc (Data-Level Taint)
    va ro ri qua cau tra loi cuoi (final_response / Markdown image exfiltration).
  - Lop 4 khong co luat rieng: no la CHE DO XU LY vi pham escalatable.
"""
import base64
import re
import sqlite3

import config

ALLOWED_DOMAINS = {config.INTERNAL_DOMAIN.lower()}
SENSITIVE_TABLES = {"salaries", "customers", "api_keys", "sqlite_master", "sqlite_temp_master"}
SENSITIVE_COLUMNS = {"base_salary", "bonus", "payroll_code", "key_value", "account_ref", "contract_value", "phone"}
SCHEMA_PREFIXES = ("pragma_",)
DENY_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}
SECRET_PATTERNS = [re.compile(r"CNRY-(SAL|CUS|KEY)-", re.I),
                   re.compile(r"sk-fake-", re.I),
                   re.compile(r"\b\d{8,}\b")]

# Phat hien anh/link ben ngoai dung de tuon du lieu qua HTTP GET (Markdown exfiltration)
EXTERNAL_LINK_RE = re.compile(r"!\[[^\]]*\]\(https?://[^)]+\)|https?://[^\s)\"'>]+", re.I)

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
                    if end != "]" and i + 1 < n and sql[i + 1] == end:
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
    """Bien dich (KHONG chay) cau SQL bang EXPLAIN tren ket noi chi-doc."""
    sql = str(sql or "")
    lex = _lex_check(sql)
    tables, hard = set(), ([lex] if lex else [])

    def authorizer(action, arg1, arg2, dbname, trigger):
        if action == _A.SQLITE_READ:
            tables.add((arg1 or "").lower())
        elif action == _A.SQLITE_FUNCTION:
            if (arg2 or "").lower() in DENY_FUNCTIONS:
                hard.append(f"ham bi cam: {arg2}")
                return _A.SQLITE_DENY
        elif action not in _ALLOWED_ACTIONS:
            hard.append(f"thao tac SQL khong duoc phep (authorizer action={action}, {arg1})")
            return _A.SQLITE_DENY
        return _A.SQLITE_OK

    uri = (db_path or config.DB_PATH).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        con.set_authorizer(authorizer)
        con.execute("EXPLAIN " + sql).fetchall()
    except sqlite3.Error as e:
        if not hard:
            hard.append(f"SQL khong bien dich duoc: {e}")
    finally:
        con.close()
    return {"hard": hard[0] if hard else None, "tables": tables}


def _sensitive(tables):
    return sorted(t for t in tables
                  if t in SENSITIVE_TABLES or t.startswith(SCHEMA_PREFIXES))


# ---------------------------------------------- Data-Level Taint & DLP helpers
def _artifact_variants(val):
    """Sinh cac bien the ma hoa pho bien (goc, Base64, Hex, dao nguoc) de chong bypass DLP."""
    s = str(val).strip()
    if len(s) < 6:
        return set()
    raw = s.encode("utf-8", errors="ignore")
    b64 = base64.b64encode(raw).decode("ascii").rstrip("=")
    hx = raw.hex()
    variants = {s.lower(), s[::-1].lower()}
    if len(b64) >= 8:
        variants.add(b64.lower())
    if len(hx) >= 10:
        variants.add(hx.lower())
    return variants


def check_dlp_text(text, state=None, is_final_response=False):
    """Kiem tra ro ri du lieu mat (Regex tinh + Data-level artifacts + Markdown URL).
    Tra ve ly do vi pham neu bi chan, nguoc lai None."""
    content = str(text or "")
    if any(p.search(content) for p in SECRET_PATTERNS):
        return "thu chua mau du lieu mat (DLP)"

    state = state or {}
    artifacts = state.get("sensitive_artifacts") or []
    lowered = content.lower()
    compact = re.sub(r"\s+", "", lowered)
    for art in artifacts:
        for var in _artifact_variants(art):
            if var in lowered or var in compact:
                return "phat hien ro ri du lieu trich xuat tu bang mat (Data-Level DLP / Anti-Obfuscation)"

    if is_final_response and state.get("tainted"):
        for url in EXTERNAL_LINK_RE.findall(content):
            if config.INTERNAL_DOMAIN.lower() not in url.lower():
                return f"chan URL/anh ngoai trong phan hoi khi phien da nhiem ban: {url[:60]}"
    return None


# ------------------------------------------------------------------- policy
def _v(decision, layer, reason, rule=None):
    return {"decision": decision, "layer": layer, "reason": reason, "rule": rule}


def make_policy(layer2=False, layer3=False, layer4=False):
    escalate = layer4

    def _escalatable(name, args, state):
        if name == "send_email":
            for addr in _recipients(args.get("to", "")):
                if addr.split("@")[-1].lower() not in ALLOWED_DOMAINS:
                    return "L2.recipient_allowlist", f"nguoi nhan ngoai allowlist: {addr}"
        if name == "query_db" and state.get("tainted"):
            hit = _sensitive(state["_sql"]["tables"])
            if hit:
                return ("L2.taint_sensitive_read",
                        f"truy van bang mat khi da nhiem noi dung ngoai: {', '.join(hit)}")
            if state["_sql"]["hard"]:
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
        # 2) Lop 2 khi KHONG co L4
        esc = _escalatable(name, args, state) if (layer2 or layer4) else None
        if esc and layer2 and not escalate:
            return _v("BLOCK", 2, esc[1], esc[0])
        # 3) HARD cua Lop 3 (DLP): quet ca Regex tinh lan Data-Level Taint (Base64/Hex/dao nguoc)
        if layer3 and name == "send_email":
            body = str(args.get("subject", "")) + " " + str(args.get("body", ""))
            dlp_err = check_dlp_text(body, state=state, is_final_response=False)
            if dlp_err:
                return _v("BLOCK", 3, dlp_err, "L3.dlp")
        # 4) Lop 4: vi pham escalatable -> hang doi duyet
        if esc and escalate:
            return _v("PENDING_APPROVAL", 4, f"cho duyet ({esc[1]})", esc[0])
        return _v("ALLOW", None, "")

    policy.spec = {"layer2": layer2, "layer3": layer3, "layer4": layer4}
    return policy