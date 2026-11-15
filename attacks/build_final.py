import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_DIR = ROOT / "attacks" / "seeds"
LOG_DIR = ROOT / "experiments" / "results_raw" / "attacker_agent_logs"
OUT_DIR = ROOT / "attacks" / "final"

OWASP = {g: "LLM01 Prompt Injection" for g in
         ("direct_override", "impersonation", "urgency",
          "hidden_instruction", "fake_system_format", "split_instruction")}
SCORE_KEYS = ("victim", "round", "doc", "queried", "sent", "leaked", "markers")


def _level(d):
    return (d.get("leaked") or 0, d.get("sent") or 0, d.get("markers") or 0)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seed_group = {}
    for f in SEED_DIR.glob("*.json"):
        s = json.loads(f.read_text(encoding="utf-8"))
        seed_group[s["id"]] = s.get("group", "?")

    by_body, order = {}, []

    def add(email, group, source, score):
        body = ((email.get("body_text") or "") + (email.get("body_html") or "")).strip()
        if not body:
            return
        if body in by_body:                       # trung -> gop diem neu lan nay manh hon
            rec = by_body[body]
            if _level(score) > _level({k: rec.get(k) for k in SCORE_KEYS}):
                rec.update({k: score.get(k, "") for k in SCORE_KEYS})
            return
        rec = {"id": None, "source": source, "group": group,
               "owasp": OWASP.get(group, "LLM01 Prompt Injection"),
               "from": email.get("from"), "subject": email.get("subject"),
               "body_text": email.get("body_text"), "body_html": email.get("body_html"),
               **{k: score.get(k, "") for k in SCORE_KEYS}}
        by_body[body] = rec
        order.append(rec)

    blank = {k: "" for k in SCORE_KEYS}
    for f in sorted(SEED_DIR.glob("*.json")):     # 1) hat giong (S)
        s = json.loads(f.read_text(encoding="utf-8"))
        add(s, s.get("group", "?"), "S", dict(blank))

    for f in sorted(LOG_DIR.glob("*.json")):      # 2) attacker-generated (A)
        log = json.loads(f.read_text(encoding="utf-8"))
        victim = log.get("victim", "?")
        group = seed_group.get(log.get("seed_id", ""), "?")
        for r, rnd in enumerate(log.get("rounds", [])):
            score = {"victim": victim, "round": r, "doc": rnd.get("doc"),
                     "queried": rnd.get("queried"), "sent": rnd.get("sent"),
                     "leaked": rnd.get("leaked"), "markers": rnd.get("distinct_markers")}
            add(rnd.get("email", {}), group, "A", score)

    rows = []
    for i, rec in enumerate(order, 1):
        rec["id"] = f"P{i:02d}_{rec['source']}_{rec['group']}"
        (OUT_DIR / f"{rec['id']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(rec)

    cols = ["id", "source", "group", "owasp", "victim", "round",
            "doc", "queried", "sent", "leaked", "markers", "from", "subject"]
    with open(OUT_DIR / "index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

    print(f"Tong payload: {len(rows)}")
    print("Theo nguon:", dict(Counter(r["source"] for r in rows)))
    print("Theo nhom :", dict(Counter(r["group"] for r in rows)))
    print("Payload tung gay RO RI that:", sum(1 for r in rows if r.get("leaked") == 1))
    print("Da luu:", OUT_DIR)


if __name__ == "__main__":
    main()