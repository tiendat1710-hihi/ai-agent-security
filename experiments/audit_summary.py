"""Read audit events for both the terminal and Streamlit."""

import json
from collections import Counter

import config

AUDIT_EVENTS = {"guardrail_decision", "human_decision", "llm_error"}
DECISION_ALIASES = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "EXPIRE": "EXPIRED",
}


def read_audit():
    rows = []
    skipped = 0
    for path in sorted(config.LOG_DIR.glob("*.jsonl"), reverse=True):
        try:
            with path.open(encoding="utf-8-sig", errors="replace") as file:
                for line in file:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        skipped += 1
                        continue
                    if not isinstance(row, dict) or "\ufffd" in line:
                        skipped += 1
                        continue
                    if row.get("event") not in AUDIT_EVENTS:
                        continue
                    decision = str(row.get("decision") or "")
                    if row["event"] == "llm_error":
                        decision = "INFRA_ERROR"
                    rows.append({
                        **row,
                        "run_id": str(row.get("run_id") or path.stem),
                        "decision": DECISION_ALIASES.get(decision, decision) or "UNKNOWN",
                        "layer": f"L{row['layer']}" if row.get("layer") in (1, 2, 3, 4) else "—",
                    })
        except OSError:
            skipped += 1
    rows.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
    return rows, skipped


def main():
    rows, skipped = read_audit()
    print(f"Su kien kiem toan: {len(rows)} | Muc khong doc duoc: {skipped}")
    for (layer, decision), count in Counter((r["layer"], r["decision"]) for r in rows).most_common():
        print(f"  {layer:<4} {decision:<18} {count}")
    print("\nLy do chan / cho duyet:")
    reasons = Counter(r["reason"] for r in rows
                      if r.get("reason") and r["decision"] in {"BLOCK", "PENDING_APPROVAL"})
    for reason, count in reasons.most_common(10):
        print(f"  [{count}] {reason}")


if __name__ == "__main__":
    main()
