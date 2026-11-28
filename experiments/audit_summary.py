"""Tong hop nhat ky kiem toan tu log JSONL (dung chung cho CLI va ui/page_audit.py).

Moi "quyet dinh" la 1 dong chuan hoa: ts, run_id, model, kind, tool, layer,
decision, rule, reason, reviewer. Trong do:
  kind = "guardrail"  : su kien guardrail_decision (ALLOW / BLOCK / PENDING_APPROVAL)
  kind = "human"      : su kien human_decision (APPROVED / REJECTED, kem expired)
"""
import argparse
import collections
import json
from pathlib import Path

import config

GUARDRAIL_DECISIONS = ("ALLOW", "BLOCK", "PENDING_APPROVAL")
HUMAN_DECISIONS = ("APPROVED", "REJECTED")


def load_rows(log_dir=None):
    """Doc moi dong cua moi file *.jsonl; bo qua dong hong. Gan them _file."""
    rows = []
    for f in sorted(Path(log_dir or config.LOG_DIR).glob("*.jsonl")):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(r, dict):
                r.setdefault("run_id", f.stem)
                rows.append(r)
    return rows


def _layer(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def decisions(rows):
    out = []
    for r in rows:
        ev = r.get("event")
        if ev == "guardrail_decision":
            kind = "guardrail"
        elif ev == "human_decision":
            kind = "human"
        else:
            continue
        decision = r.get("decision")
        if kind == "human" and r.get("expired"):
            decision = "REJECTED"
        out.append({
            "ts": r.get("ts"), "run_id": r.get("run_id"), "model": r.get("model"),
            "kind": kind, "tool": r.get("tool"), "layer": _layer(r.get("layer")),
            "decision": decision, "rule": r.get("rule"), "reason": r.get("reason") or "",
            "reviewer": r.get("reviewer"), "expired": bool(r.get("expired")),
            "args": r.get("args"),
        })
    return out


def filter_decisions(decs, layers=None, decisions_=None, models=None):
    """layers: tap {1,2,3,4}; decisions_: tap gom ALLOW/BLOCK/PENDING_APPROVAL/
    APPROVED/REJECTED; None = khong loc."""
    out = []
    for d in decs:
        if layers is not None and d["layer"] not in layers:
            continue
        if decisions_ is not None and d["decision"] not in decisions_:
            continue
        if models is not None and d["model"] not in models:
            continue
        out.append(d)
    return out


def summarize(decs, top=10):
    by_dl = collections.Counter((d["decision"], d["layer"]) for d in decs)
    blocked = [d for d in decs if d["decision"] in ("BLOCK", "PENDING_APPROVAL")]
    reasons = collections.Counter(d["reason"] for d in blocked)
    rules = collections.Counter(d["rule"] or "(khong ghi)" for d in blocked)
    human = [d for d in decs if d["kind"] == "human"]
    return {
        "total": len(decs),
        "by_decision_layer": by_dl,
        "top_reasons": reasons.most_common(top),
        "top_rules": rules.most_common(top),
        "human": {
            "approved": sum(d["decision"] == "APPROVED" for d in human),
            "rejected": sum(d["decision"] == "REJECTED" and not d["expired"] for d in human),
            "expired": sum(d["expired"] for d in human),
            "auto": sum(d["reviewer"] == "auto" for d in human),
        },
        "runs": len({d["run_id"] for d in decs}),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--layer", type=int, action="append", help="loc lop (lap lai duoc)")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args(argv)

    rows = load_rows(a.log_dir)
    decs = decisions(rows)
    if a.layer:
        decs = filter_decisions(decs, layers=set(a.layer))
    s = summarize(decs, a.top)
    print(f"Tong su kien log: {len(rows)} | quyet dinh: {s['total']} | so phien: {s['runs']}")

    print("\n== Theo (quyet dinh, lop) ==")
    for (d0, layer), n in sorted(s["by_decision_layer"].items(), key=lambda x: -x[1]):
        print(f"  {str(d0):<18} Lop {layer}: {n}")

    h = s["human"]
    print(f"\n== Nguoi duyet (Lop 4) ==\n  APPROVED {h['approved']} (auto {h['auto']}) | "
          f"REJECTED {h['rejected']} | het han {h['expired']}")

    print("\n== Luat chan / treo (top) ==")
    for rule, n in s["top_rules"]:
        print(f"  [{n}] {rule}")
    print("\n== Ly do chan / treo (top) ==")
    for reason, n in s["top_reasons"]:
        print(f"  [{n}] {reason}")
    return s


if __name__ == "__main__":
    main()
