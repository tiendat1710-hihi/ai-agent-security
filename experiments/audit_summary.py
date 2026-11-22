"""Tong hop nhat ky kiem toan: thong ke cac quyet dinh Guardrails tu log JSONL."""
import collections
import glob
import json

import config


def main():
    rows = []
    for f in glob.glob(str(config.LOG_DIR / "*.jsonl")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    dec = [r for r in rows if r.get("event") == "guardrail_decision"]
    print(f"Tong su kien log: {len(rows)} | quyet dinh Guardrails: {len(dec)}")

    print("\n== Theo (quyet dinh, lop) ==")
    by = collections.Counter((d.get("decision"), d.get("layer")) for d in dec)
    for (d0, layer), n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {str(d0):<18} Lop {layer}: {n}")

    print("\n== Ly do chan (top) ==")
    reasons = collections.Counter(d.get("reason") for d in dec if d.get("decision") != "ALLOW")
    for reason, n in reasons.most_common(10):
        print(f"  [{n}] {reason}")


if __name__ == "__main__":
    main()