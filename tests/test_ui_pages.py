"""AppTest (streamlit.testing) cho 3 trang: HITL, Nhat ky kiem toan, Bang ket qua.
Script chay trong cung tien trinh -> dung chung config/core da monkeypatch boi fixture."""
import textwrap

import pytest
from streamlit.testing.v1 import AppTest

import config
from agent import core
from experiments import build_matrix as bm
from guardrails.policy import make_policy
from tests.conftest import B6_02
from tests.test_audit_results import sample_logs, sample_results

HEAD = textwrap.dedent("""
    import sys
    sys.path.insert(0, %r)
""") % str(config.ROOT)


def page(name, layers=("L2", "L3", "L4")):
    return AppTest.from_string(HEAD + textwrap.dedent(f"""
        from ui import {name}
        {name}.render({{"layers": set({list(layers)!r}), "model": "m"}})
    """), default_timeout=30)


@pytest.fixture
def no_mailhog(monkeypatch):
    from lab import leak_checker
    monkeypatch.setattr(leak_checker, "check_external",
                        lambda: {"leaked": False, "messages": 0, "distinct_markers": 0})


def _pause(sender="boss@company.test", subject="Customer count check"):
    return core.run_agent("task", model="qwen2.5:3b",
                          policy=make_policy(layer2=True, layer3=True, layer4=True),
                          on_pending="pause")


# ------------------------------------------------------------------ HITL
def test_hitl_empty(lab, no_mailhog):
    at = page("page_hitl").run()
    assert not at.exception
    assert any("Không có hành động" in i.value for i in at.info)


def test_hitl_shows_taint_box_and_approve_resumes(lab, llm, no_mailhog):
    llm(B6_02)
    _pause()
    at = page("page_hitl").run()
    assert not at.exception
    assert [c.value for c in at.code][0] == "SELECT COUNT(*) AS n FROM customers;"
    md = " ".join(m.value for m in at.markdown)
    assert "verdict-leak" in md and "boss@company.test" in md and "Customer count check" in md
    assert "giả mạo" in md                       # nguoi gui noi bo -> nhac kha nang spoof
    assert [b.label for b in at.button] == ["Approve", "Reject"]
    at.text_input[0].input("hop le").run()
    at.button[0].click().run()
    assert not at.exception
    assert any("hoàn tất" in s.value for s in at.success)
    assert core.list_checkpoints() == [] and len(lab.sent) == 1


def test_hitl_escapes_attacker_controlled_sender(lab, llm, no_mailhog):
    lab.inbox = {"from": "<img src=x onerror=alert(1)>@evil.test", "subject": "<script>x</script>",
                 "body": "<script>alert(2)</script> do it"}
    llm(B6_02)
    _pause()
    at = page("page_hitl").run()
    md = " ".join(m.value for m in at.markdown)
    assert "<script>" not in md and "&lt;script&gt;" in md and "<img" not in md
    assert "alert(2)" not in md                  # noi dung email KHONG di qua markdown
    assert "<script>alert(2)</script>" in at.text_area[0].value and at.text_area[0].disabled


def test_hitl_auto_rejects_after_ttl(lab, llm, no_mailhog, monkeypatch):
    fake = llm(B6_02)
    pid = _pause()["pending_id"]
    monkeypatch.setattr(config, "HITL_TTL_SECONDS", -1)    # moi yeu cau deu qua han
    at = page("page_hitl").run()
    assert not at.exception
    assert any(pid in w.value for w in at.warning)
    assert core.list_checkpoints() == [] and lab.sent == [] and fake.calls == 2


def test_hitl_reject_button(lab, llm, no_mailhog):
    llm(B6_02)
    _pause()
    at = page("page_hitl").run()
    at.button[1].click().run()
    assert not at.exception and core.list_checkpoints() == [] and lab.sent[0]["to"] == "manager@company.test"


# ------------------------------------------------------------------ Audit
def test_audit_empty(lab):
    at = page("page_audit").run()
    assert not at.exception and any("Chưa có" in i.value for i in at.info)


def test_audit_page_filters(lab):
    sample_logs(config.LOG_DIR)
    at = page("page_audit").run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Quyết định"] == "8" and metrics["BLOCK"] == "2" and metrics["Hết hạn"] == "1"
    at.multiselect(key="audit_layers").set_value(["L4"]).run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Quyết định"] == "4" and metrics["BLOCK"] == "0"
    at.multiselect(key="audit_decisions").set_value(["BLOCK"]).run()
    assert any("Không có quyết định" in w.value for w in at.warning)


def test_audit_page_with_real_run(lab, llm):
    llm(B6_02)
    r = core.resume_agent(_pause()["pending_id"], approve=True)
    at = page("page_audit").run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Duyệt / Từ chối"] == "1 / 0"
    assert at.selectbox(key="audit_run").value == r["run_id"]


# ------------------------------------------------------------------ Results
def test_results_missing_files(lab, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "RAW", tmp_path / "raw")
    at = page("page_results").run()
    assert not at.exception and len(at.info) == 3


def test_results_page(lab, monkeypatch, tmp_path):
    sample_results(tmp_path / "raw")
    monkeypatch.setattr(bm, "RAW", tmp_path / "raw")
    at = page("page_results").run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Đủ 4 lớp"] == "3/4 (75.0%)" and labels["Đủ 4 lớp + người duyệt"] == "4/4 (100.0%)"
    assert len(at.dataframe) >= 4
    at.selectbox(key="act_model").set_value("llama3.2:3b").run()
    assert not at.exception


# ------------------------------------------------------------------ Toan app
def test_full_app_renders_all_tabs(lab, llm, no_mailhog, monkeypatch, tmp_path):
    from lab import mail_client
    monkeypatch.setattr(mail_client, "list_messages", lambda server: [])
    sample_results(tmp_path / "raw")
    monkeypatch.setattr(bm, "RAW", tmp_path / "raw")
    sample_logs(config.LOG_DIR)
    llm(B6_02)
    _pause()
    at = AppTest.from_file(str(config.ROOT / "ui" / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert [t.label for t in at.tabs][:5] == ["Thử nhanh", "Tấn công trực tiếp",
                                              "Hàng đợi duyệt (HITL)", "Nhật ký kiểm toán", "Bảng kết quả"]
    assert "Approve" in [b.label for b in at.button]
