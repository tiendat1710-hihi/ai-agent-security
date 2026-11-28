import csv
import glob
import os
import re
from pathlib import Path

import config

RAW = config.ROOT / "experiments" / "results_raw"
ORDER = ["none", "L1", "L2", "L3", "L4", "all"]


def label_of(path):
    stem = Path(path).stem  # asr_L2_20261115_1833
    m = re.match(r"asr_(.+?)_\d{8}_\d{4}$", stem)
    lbl = m.group(1) if m else stem[4:]
    return "none" if lbl == "baseline" else lbl


def newest_per_label():
    latest = {}
    for f in glob.glob(str(RAW / "asr_*.csv")):
        lbl = label_of(f)
        if lbl not in latest or os.path.getmtime(f) > os.path.getmtime(latest[lbl]):
            latest[lbl] = f
    return latest


def newest(pattern):
    fs = glob.glob(str(RAW / pattern))
    return max(fs, key=os.path.getmtime) if fs else None


def read_asr():
    latest = newest_per_label()
    data = {}          # (model, group) -> {label: (action, leak)}
    models, groups = [], []
    for lbl in [l for l in ORDER if l in latest] + [l for l in latest if l not in ORDER]:
        for r in csv.DictReader(open(latest[lbl], encoding="utf-8")):
            m, g = r["model"], r["group"]
            if m not in models:
                models.append(m)
            if g not in groups:
                groups.append(g)
            data.setdefault((m, g), {})[lbl] = (
                float(r["ASR_action_%"]), float(r["ASR_leak_%"]),
            )
    cols = [l for l in ORDER if l in latest] + [l for l in latest if l not in ORDER]
    return data, models, groups, cols, latest


def completion(path):
    out = {}
    if not path:
        return out
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r.get("error"):
            continue
        m = r["model"]
        out.setdefault(m, [0, 0])
        out[m][0] += int(r["success"])
        out[m][1] += 1
    return out


# ----------------------------------------------- doc lai cho ui/page_results.py
def utility_label(path):
    """utility_all_t0.0_20261122_1436.csv -> 'all'; utility_hitlok-all_t0.0_... -> 'hitlok-all'."""
    m = re.match(r"utility_(.+?)_t[\d.]+_\d{8}_\d{4}$", Path(path).stem)
    return m.group(1) if m else None


def newest_utility_per_label(raw=None):
    latest = {}
    for f in glob.glob(str(Path(raw or RAW) / "utility_*.csv")):
        lbl = utility_label(f)
        if lbl and (lbl not in latest or os.path.getmtime(f) > os.path.getmtime(latest[lbl])):
            latest[lbl] = f
    return latest


def utility_rows(raw=None):
    """[{config, model, done, total, rate, failed_cases, file}] - moi cau hinh lay file moi nhat."""
    out = []
    latest = newest_utility_per_label(raw)
    for lbl in sorted(latest, key=lambda l: (ORDER.index(l) if l in ORDER else len(ORDER), l)):
        per_model, failed = {}, {}
        for r in csv.DictReader(open(latest[lbl], encoding="utf-8")):
            if r.get("error"):
                continue
            m = r["model"]
            c = per_model.setdefault(m, [0, 0])
            ok = int(r.get("success") or 0)
            c[0] += ok
            c[1] += 1
            if not ok:
                failed.setdefault(m, []).append(r.get("case"))
        for m, (done, total) in per_model.items():
            out.append({"config": lbl, "model": m, "done": done, "total": total,
                        "rate": round(100 * done / total, 1) if total else None,
                        "failed_cases": ", ".join(failed.get(m, [])),
                        "file": Path(latest[lbl]).name})
    return out


def read_matrix(path):
    """Doc matrix_asr_*.csv (dang rong) -> (cols, [{model, ky_thuat, <col>: float|None}])."""
    path = Path(path)
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        cols = [c for c in (rd.fieldnames or []) if c not in ("model", "ky_thuat")]
        rows = []
        for r in rd:
            row = {"model": r["model"], "ky_thuat": r["ky_thuat"]}
            for c in cols:
                v = (r.get(c) or "").strip()
                row[c] = float(v) if v else None
            rows.append(row)
    return cols, rows


def print_matrix(title, idx, data, models, groups, cols):
    print(f"\n==== {title} ====")
    for m in models:
        print(f"\n-- {m} --")
        print(f"{'ky thuat':<22}" + "".join(f"{c:>8}" for c in cols))
        for g in groups:
            cell = data.get((m, g), {})
            line = f"{g[:21]:<22}"
            for c in cols:
                v = cell.get(c)
                line += f"{(f'{v[idx]:.0f}') if v else '-':>8}"
            print(line)
        # trung binh moi cot
        line = f"{'TRUNG BINH':<22}"
        for c in cols:
            vals = [data[(m, g)][c][idx] for g in groups if c in data.get((m, g), {})]
            line += f"{(f'{sum(vals)/len(vals):.0f}') if vals else '-':>8}"
        print(line)


def write_csv(path, idx, data, models, groups, cols):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "ky_thuat"] + cols)
        for m in models:
            for g in groups:
                cell = data.get((m, g), {})
                w.writerow([m, g] + [(f"{cell[c][idx]:.0f}" if c in cell else "") for c in cols])


if __name__ == "__main__":
    data, models, groups, cols, latest = read_asr()
    print("Nguon ASR dung (moi lop lay file moi nhat):")
    for c in cols:
        print(f"  {c:<6} <- {Path(latest[c]).name}")

    print_matrix("ASR-ACTION (% hijack gui ra ngoai)", 0, data, models, groups, cols)
    print_matrix("ASR-LEAK (% ro ri du lieu that)", 1, data, models, groups, cols)

    none_c = completion(newest("utility_none_*.csv"))
    all_c = completion(newest("utility_all_*.csv"))
    print("\n==== UTILITY (ty le hoan thanh tac vu lanh) ====")
    print(f"{'model':<20}{'none':>10}{'all':>10}{'giam':>10}")
    for m in models:
        n = none_c.get(m)
        a = all_c.get(m)
        nr = 100 * n[0] / n[1] if n else None
        ar = 100 * a[0] / a[1] if a else None
        drop = (nr - ar) if (nr is not None and ar is not None) else None
        print(f"{m:<20}"
              f"{(f'{n[0]}/{n[1]}') if n else '-':>10}"
              f"{(f'{a[0]}/{a[1]}') if a else '-':>10}"
              f"{(f'{drop:.0f}%') if drop is not None else '-':>10}")

    write_csv(RAW / "matrix_asr_action.csv", 0, data, models, groups, cols)
    write_csv(RAW / "matrix_asr_leak.csv", 1, data, models, groups, cols)
    print("\nDa luu: matrix_asr_action.csv & matrix_asr_leak.csv trong results_raw")