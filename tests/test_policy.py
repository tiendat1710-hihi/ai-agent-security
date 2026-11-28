import pytest

import config
from guardrails.policy import analyze_sql, make_policy

T, C = {"tainted": True}, {"tainted": False}


@pytest.fixture(autouse=True)
def _db(lab):
    pass


@pytest.mark.parametrize("sql,tables", [
    ("SELECT COUNT(*) FROM customers", {"customers"}),
    ("WITH x AS (SELECT * FROM api_keys) SELECT count(*) FROM x", {"api_keys"}),
    ("SELECT e.full_name FROM employees e WHERE e.id IN (SELECT employee_id FROM salaries)",
     {"employees", "salaries"}),
    ("SELECT sql FROM sqlite_schema", {"sqlite_master"}),
    ('SELECT * FROM "API_KEYS"', {"api_keys"}),
    ("SELECT * FROM main.salaries", {"salaries"}),
    ("SELECT 'customers' AS x FROM employees", {"employees"}),
])
def test_authorizer_sees_real_tables(sql, tables):
    r = analyze_sql(sql)
    assert r["hard"] is None and r["tables"] == tables


@pytest.mark.parametrize("sql,needle", [
    ("SELECT * FROM employees -- AND api_keys", "comment"),
    ("SELECT * FROM employees /* x */", "comment"),
    ("SELECT 1; SELECT * FROM api_keys", "multi-statement"),
    ("PRAGMA table_info(api_keys)", "khong duoc phep"),
    ("ATTACH 'x.db' AS x", "khong duoc phep"),
    ("DELETE FROM employees", "khong duoc phep"),
    ("SELECT load_extension('x')", "ham bi cam"),
    ("SELECT * FROM nosuch", "khong bien dich"),
    ("SELECT 'abc FROM employees", "khong dong"),
])
def test_hard_sql_violations(sql, needle):
    v = make_policy(layer2=True, layer4=True)("query_db", {"sql": sql}, C)
    assert v["decision"] == "BLOCK" and v["layer"] == 2 and needle in v["reason"]


def test_trailing_semicolon_and_literals_allowed():
    pol = make_policy(layer2=True)
    assert pol("query_db", {"sql": "SELECT department FROM employees;"}, T)["decision"] == "ALLOW"
    assert pol("query_db", {"sql": "SELECT ';--' FROM employees"}, T)["decision"] == "ALLOW"


def test_l2_blocks_l4_escalates_tainted_sensitive_read():
    q = {"sql": "SELECT COUNT(*) FROM customers"}
    assert make_policy(layer2=True)("query_db", q, T)["decision"] == "BLOCK"
    v = make_policy(layer2=True, layer3=True, layer4=True)("query_db", q, T)
    assert (v["decision"], v["layer"], v["rule"]) == ("PENDING_APPROVAL", 4, "L2.taint_sensitive_read")
    assert make_policy(layer2=True, layer4=True)("query_db", q, C)["decision"] == "ALLOW"


def test_l4_only_cannot_be_bypassed_with_comment():
    v = make_policy(layer4=True)("query_db", {"sql": "SELECT * FROM api_keys -- x"}, T)
    assert v["decision"] == "PENDING_APPROVAL"


@pytest.mark.parametrize("layers,to,body,expect", [
    (dict(layer2=True), "x@evil.test", "hi", ("BLOCK", 2)),
    (dict(layer4=True), "x@evil.test", "hi", ("PENDING_APPROVAL", 4)),
    (dict(layer2=True, layer3=True, layer4=True), "x@evil.test", "hi", ("PENDING_APPROVAL", 4)),
    (dict(layer2=True, layer3=True, layer4=True), "x@evil.test", "sk-fake-CNRY-KEY-001", ("BLOCK", 3)),
    (dict(layer2=True, layer3=True), "manager@company.test", "sk-fake-1", ("BLOCK", 3)),
    (dict(layer2=True, layer3=True, layer4=True), "manager@company.test", "50", ("ALLOW", None)),
])
def test_send_email_layering(layers, to, body, expect):
    v = make_policy(**layers)("send_email", {"to": to, "subject": "s", "body": body}, T)
    assert (v["decision"], v["layer"]) == expect


def test_policy_has_spec_for_resume():
    assert make_policy(layer2=True, layer4=True).spec == {"layer2": True, "layer3": False, "layer4": True}
