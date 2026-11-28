"""Chuoi bam SHA-256 cua nhat ky kiem toan: ghi, kiem tra, phat hien sua/xoa/chen/dao dong."""
import json
import os

import pytest
from streamlit.testing.v1 import AppTest

import config
from agent import core
from experiments import logger as lg
from experiments.logger import GENESIS, RunLogger, entry_hash, verify_file, verify_recent
from guardrails.policy import make_policy
from tests.conftest import B6_02


def _log(lab_dir, n=4, run_id="r1"):
    log = RunLogger("m", run_id=run_id)
    for i in range(n):
        log.emit("tool_call", tool="query_db", args={"sql": f"SELECT {i}"}, reason=f"buoc {i}")
    return log.path


def _lines(p):
    return p.read_text(encoding="utf-8").splitlines()


def _write(p, lines):
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ ghi
def test_each_entry_links_to_previous(lab):
    p = _log(config.LOG_DIR)
    rows = [json.loads(l) for l in _lines(p)]
    assert rows[0]["prev_hash"] == GENESIS
    for a, b in zip(rows, rows[1:]):
        assert b["prev_hash"] == a["entry_hash"]
    assert all(entry_hash(r) == r["entry_hash"] and len(r["entry_hash"]) == 64 for r in rows)


def test_hash_fields_cannot_be_injected_via_kwargs(lab):
    log = RunLogger("m", run_id="inj")
    log.emit("x", prev_hash="f" * 64, entry_hash="e" * 64)
    r = json.loads(_lines(log.path)[0])
    assert r["prev_hash"] == GENESIS and r["entry_hash"] == entry_hash(r)


def test_chain_continues_across_loggers_on_same_file(lab, llm):
    """resume_agent mo RunLogger moi tren cung run_id: chuoi khong duoc dut."""
    llm(B6_02)
    r = core.run_agent("t", model="m", on_pending="pause",
                       policy=make_policy(layer2=True, layer3=True, layer4=True))
    core.resume_agent(r["pending_id"], approve=True)
    v = verify_file(config.LOG_DIR / f"{r['run_id']}.jsonl")
    assert v["status"] == "OK" and v["entries"] > 8


def test_canonical_is_key_order_independent():
    a = {"b": 1, "a": "ư", "prev_hash": GENESIS}
    b = {"prev_hash": GENESIS, "a": "ư", "b": 1}
    assert entry_hash(a) == entry_hash(b)


# ------------------------------------------------------------------ kiem tra
def test_intact_file_ok(lab):
    p = _log(config.LOG_DIR)
    v = verify_file(p)
    assert (v["status"], v["entries"], v["bad_line"]) == ("OK", 4, None)
    assert v["head"] == json.loads(_lines(p)[-1])["entry_hash"]


@pytest.mark.parametrize("attack,bad_line,needle", [
    ("edit_field", 2, "bi sua"),
    ("delete_middle", 2, "prev_hash"),
    ("swap", 2, "prev_hash"),
    ("insert_forged", 3, "prev_hash"),
    ("drop_hashes", 3, "thieu"),
    ("garbage", 2, "JSON"),
    ("delete_first", 1, "prev_hash"),
])
def test_tampering_detected(lab, attack, bad_line, needle):
    p = _log(config.LOG_DIR)
    L = _lines(p)
    if attack == "edit_field":
        r = json.loads(L[1]); r["reason"] = "da bi sua"; L[1] = json.dumps(r, ensure_ascii=False)
    elif attack == "delete_middle":
        del L[1]
    elif attack == "swap":
        L[1], L[2] = L[2], L[1]
    elif attack == "insert_forged":
        # dong gia co entry_hash tu tinh dung, nhung prev_hash tro sai cho
        f = {"event": "human_decision", "decision": "APPROVED", "prev_hash": GENESIS}
        f["entry_hash"] = entry_hash(f)
        L.insert(2, json.dumps(f))
    elif attack == "drop_hashes":
        r = json.loads(L[2]); r.pop("prev_hash"); r.pop("entry_hash"); L[2] = json.dumps(r)
    elif attack == "garbage":
        L[1] = L[1][:-5]
    elif attack == "delete_first":
        del L[0]
    _write(p, L)
    v = verify_file(p)
    assert v["status"] == "BROKEN" and v["bad_line"] == bad_line and needle in v["reason"]
    assert v["head"] is None             # khong hien bam cuoi chuoi cho file hong


def test_recomputing_whole_chain_is_a_known_limitation(lab):
    """Ghi lai gioi han da neu trong UI: khong co khoa bi mat -> tinh lai ca chuoi thi qua."""
    p = _log(config.LOG_DIR)
    rows = [json.loads(l) for l in _lines(p)]
    rows[1]["reason"] = "sua roi tinh lai"
    prev = GENESIS
    for r in rows:
        r["prev_hash"] = prev
        r["entry_hash"] = entry_hash(r)
        prev = r["entry_hash"]
    _write(p, [json.dumps(r, ensure_ascii=False) for r in rows])
    assert verify_file(p)["status"] == "OK"


def test_legacy_empty_and_blank_lines(lab):
    d = config.LOG_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "old.jsonl").write_text('{"event": "x"}\n{"event": "y"}\n', encoding="utf-8")
    (d / "empty.jsonl").write_text("\n\n", encoding="utf-8")
    p = _log(d, run_id="blank")
    _write(p, [l for pair in zip(_lines(p), [""] * 9) for l in pair])   # chen dong trong
    assert verify_file(d / "old.jsonl")["status"] == "UNCHAINED"
    (d / "old_bad.jsonl").write_text('{"event": "x"}\n{hong\n', encoding="utf-8")
    v = verify_file(d / "old_bad.jsonl")
    assert (v["status"], v["bad_line"], v["head"]) == ("UNCHAINED", 2, None) and "hong" in v["reason"]
    assert verify_file(d / "empty.jsonl")["status"] == "EMPTY"
    assert verify_file(p)["status"] == "OK"


def test_verify_recent_orders_by_mtime_and_limits(lab):
    paths = [_log(config.LOG_DIR, n=1, run_id=f"f{i}") for i in range(5)]
    for i, p in enumerate(paths):
        os.utime(p, (1_000_000 + i, 1_000_000 + i))
    res = verify_recent(limit=3)
    assert [r["run_id"] for r in res] == ["f4", "f3", "f2"]
    assert verify_recent(log_dir=config.LOG_DIR / "nope") == []


# ------------------------------------------------------------------ UI
def _page():
    return AppTest.from_string(
        f"import sys\nsys.path.insert(0, {str(config.ROOT)!r})\n"
        "from ui import page_audit\npage_audit.render({'layers': set(), 'model': 'm'})\n",
        default_timeout=30)


def _btn(at):
    return next(b for b in at.button if b.label == "Kiểm tra tính toàn vẹn Log (SHA-256)")


def test_ui_button_reports_intact_logs(lab):
    _log(config.LOG_DIR, run_id="a")
    _log(config.LOG_DIR, run_id="b")
    at = _page().run()
    assert not at.exception and not at.success      # chua bam thi chua kiem tra
    _btn(at).click().run()
    assert not at.exception
    assert at.success and "2/2" in at.success[0].value and "8 dòng" in at.success[0].value
    assert not at.error


def test_ui_button_flags_tampered_file(lab):
    _log(config.LOG_DIR, run_id="good")
    p = _log(config.LOG_DIR, run_id="evil")
    L = _lines(p)
    r = json.loads(L[2]); r["decision"] = "APPROVED"; L[2] = json.dumps(r)
    _write(p, L)
    at = _page().run()
    _btn(at).click().run()
    assert not at.exception
    assert at.error and "1/2" in at.error[0].value and "evil.jsonl (dòng 3)" in at.error[0].value


def test_ui_button_limit_and_empty(lab):
    at = _page().run()
    _btn(at).click().run()
    assert any("Không có file log" in i.value for i in at.info)
    for i in range(3):
        p = _log(config.LOG_DIR, n=1, run_id=f"x{i}")
        os.utime(p, (2_000_000 + i, 2_000_000 + i))
    at = _page().run()
    at.number_input(key="integrity_limit").set_value(1).run()
    _btn(at).click().run()
    assert "1/1" in at.success[0].value
