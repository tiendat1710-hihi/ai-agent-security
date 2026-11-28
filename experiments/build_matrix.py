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
    m = re.match(r"asr_(.+?)_\d{8}_\d{4}(?:\d{2})?$", stem)
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
            if r["ASR_action_%"] and r["ASR_leak_%"]:
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
