import csv
import json

from experiments import audit_summary as au
from experiments import build_matrix as bm


def write_log(d, run_id, rows):
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{run_id}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"run_id": run_id, "model": "m", **r}) + "\n")
        f.write("{hong json\n\n")


def sample_logs(d):
    write_log(d, "r1", [
        {"event": "user_request"},
        {"event": "guardrail_decision", "decision": "ALLOW", "layer": 1, "rule": "L1.sanitize_spotlight", "reason": "lam sach"},
        {"event": "guardrail_decision", "decision": "ALLOW", "layer": None, "reason": ""},
        {"event": "guardrail_decision", "decision": "BLOCK", "layer": 2, "rule": "L2.taint_sensitive_read", "reason": "bang mat"},
        {"event": "guardrail_decision", "decision": "BLOCK", "layer": 3, "rule": "L3.dlp", "reason": "DLP"},
    ])
    write_log(d, "r2", [
        {"event": "guardrail_decision", "decision": "PENDING_APPROVAL", "layer": 4, "rule": "L2.taint_sensitive_read", "reason": "bang mat"},
        {"event": "human_decision", "decision": "APPROVED", "layer": 4, "reviewer": "ui"},
        {"event": "guardrail_decision", "decision": "PENDING_APPROVAL", "layer": 4, "rule": "L2.recipient_allowlist", "reason": "ngoai"},
        {"event": "human_decision", "decision": "REJECTED", "layer": 4, "reviewer": "system", "expired": True},
    ])


def test_audit_counts_and_filters(tmp_path):
    sample_logs(tmp_path)
    decs = au.decisions(au.load_rows(tmp_path))
    assert len(decs) == 8
    s = au.summarize(decs)
    assert s["by_decision_layer"][("BLOCK", 2)] == 1
    assert s["by_decision_layer"][("PENDING_APPROVAL", 4)] == 2
    assert s["human"] == {"approved": 1, "rejected": 0, "expired": 1, "auto": 0}
    assert s["top_reasons"][0] == ("bang mat", 2)
    assert dict(s["top_rules"])["L2.taint_sensitive_read"] == 2
    assert len(au.filter_decisions(decs, layers={1})) == 1
    assert len(au.filter_decisions(decs, layers={None})) == 1
    assert len(au.filter_decisions(decs, decisions_={"APPROVED", "REJECTED"})) == 2


def test_audit_cli(tmp_path, capsys):
    sample_logs(tmp_path)
    au.main(["--log-dir", str(tmp_path), "--layer", "4"])
    out = capsys.readouterr().out
    assert "APPROVED 1" in out and "het han 1" in out and "L2.recipient_allowlist" in out


def sample_results(raw):
    raw.mkdir(parents=True, exist_ok=True)
    with open(raw / "matrix_asr_action.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "ky_thuat", "none", "L3", "L4", "all"])
        w.writerow(["qwen2.5:3b", "urgency", "40", "17", "0", "0"])
        w.writerow(["llama3.2:3b", "urgency", "90", "70", "", "0"])
    with open(raw / "matrix_asr_leak.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "ky_thuat", "none", "L3", "L4", "all"])
        w.writerow(["qwen2.5:3b", "urgency", "30", "0", "0", "0"])
        w.writerow(["llama3.2:3b", "urgency", "80", "0", "", "0"])
    fields = ["model", "case", "group", "rep", "success", "error"]
    for name, fails in [("utility_none_t0.0_20261122_1422.csv", set()),
                        ("utility_all_t0.0_20261122_1436.csv", {"b6_02"}),
                        ("utility_hitlok-all_t0.0_20261129_1000.csv", set())]:
        with open(raw / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for m in ["qwen2.5:3b", "llama3.2:3b"]:
                for c in ["b1_01", "b6_02"]:
                    w.writerow({"model": m, "case": c, "group": "g", "rep": 1,
                                "success": int(not (m == "qwen2.5:3b" and c in fails)), "error": ""})


def test_results_readers(tmp_path):
    sample_results(tmp_path)
    cols, rows = bm.read_matrix(tmp_path / "matrix_asr_action.csv")
    assert cols == ["none", "L3", "L4", "all"] and rows[1]["L4"] is None and rows[0]["L3"] == 17.0
    assert bm.read_matrix(tmp_path / "missing.csv") == ([], [])
    ut = {(r["config"], r["model"]): r for r in bm.utility_rows(tmp_path)}
    assert ut[("all", "qwen2.5:3b")]["done"] == 1 and ut[("all", "qwen2.5:3b")]["failed_cases"] == "b6_02"
    assert ut[("hitlok-all", "qwen2.5:3b")]["rate"] == 100.0
    assert [r["config"] for r in bm.utility_rows(tmp_path)][:2] == ["none", "none"]
