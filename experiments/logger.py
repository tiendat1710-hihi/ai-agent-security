import hashlib
import json
import threading
import time
import uuid
from pathlib import Path

import config

# ---------------------------------------------------------- chuoi bam SHA-256
# Moi dong log mang prev_hash (= entry_hash cua dong truoc trong CUNG file, dong dau
# = GENESIS) va entry_hash = SHA-256 cua dong do o dang JSON chuan hoa (sort_keys,
# khong khoang trang), tinh tren moi truong TRU entry_hash. Sua noi dung, xoa, chen
# hay dao thu tu dong deu lam dut chuoi.
# Gioi han: khong co khoa bi mat -> ai sua duoc file VA tinh lai toan bo chuoi tu
# diem sua tro di thi van qua kiem tra; cat bot cac dong CUOI file cung khong lo
# (khong co moc ngoai). Day la phat hien sua vo y / sua tay, khong phai chong gia mao.
GENESIS = "0" * 64
HASH_FIELDS = ("prev_hash", "entry_hash")
_WRITE_LOCK = threading.Lock()   # Streamlit chay nhieu luong: doc-duoi + ghi phai nguyen tu


def canonical(row):
    body = {k: v for k, v in row.items() if k != "entry_hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def entry_hash(row):
    return hashlib.sha256(canonical(row).encode("utf-8")).hexdigest()


def _last_hash(path):
    """entry_hash cua dong cuoi file (resume_agent mo logger moi tren cung file)."""
    if not path.exists():
        return GENESIS
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            try:
                return json.loads(line).get("entry_hash") or GENESIS
            except (json.JSONDecodeError, AttributeError):
                return GENESIS
    return GENESIS


class RunLogger:
    """Ghi 1 lan chay agent thanh file JSONL theo dung hop dong interfaces.md."""

    def __init__(self, model, run_id=None):
        self.model = model
        self.run_id = run_id or uuid.uuid4().hex[:8]
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = config.LOG_DIR / f"{self.run_id}.jsonl"
        self._t0 = time.time()

    def emit(self, event, tool=None, args=None, result_preview=None,
             decision=None, layer=None, reason=None, **kwargs):
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_id": self.run_id,
            "model": self.model,
            "event": event,
            "tool": tool,
            "args": args,
            "result_preview": result_preview,
            "decision": decision,
            "layer": layer,
            "reason": reason,
            "latency_ms": round((time.time() - self._t0) * 1000),
        }
        # truong mo rong (rule, pending_id, reviewer, step...) cho trang Nhat ky kiem toan
        row.update({k: v for k, v in kwargs.items() if k not in row and k not in HASH_FIELDS})
        with _WRITE_LOCK:
            row["prev_hash"] = _last_hash(self.path)
            row["entry_hash"] = entry_hash(row)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._t0 = time.time()


def read_run(run_id_or_path):
    """Doc 1 file log, tra ve danh sach dict (dung cho UI va cho phan tich)."""
    p = Path(run_id_or_path)
    if not p.exists():
        p = config.LOG_DIR / f"{run_id_or_path}.jsonl"
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:   # dong hong (tien trinh bi ngat giua luc ghi) khong lam sap UI
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def list_runs(limit=20):
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(config.LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [f.stem for f in files[:limit]]

# ---------------------------------------------------------- kiem tra toan ven
def verify_file(path):
    """Kiem tra chuoi prev_hash -> entry_hash cua 1 file .jsonl.
    status: OK | BROKEN | UNCHAINED (log cu, chua co chuoi bam) | EMPTY."""
    path = Path(path)
    out = {"file": path.name, "run_id": path.stem, "status": "OK", "entries": 0,
           "bad_line": None, "reason": "", "head": GENESIS}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return {**out, "status": "BROKEN", "head": None, "reason": f"khong doc duoc file: {e}"}
    rows = []      # (so dong, dict) ; dict = None neu dong khong phai JSON object
    for no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            r = None
        rows.append((no, r if isinstance(r, dict) else None))
    if not rows:
        return {**out, "status": "EMPTY", "head": None}
    if not any(r and "entry_hash" in r for _, r in rows):
        bad = [no for no, r in rows if r is None]
        return {**out, "status": "UNCHAINED", "entries": len(rows) - len(bad), "head": None,
                "bad_line": bad[0] if bad else None,
                "reason": "log tao truoc khi co chuoi bam, khong kiem tra duoc"
                          + (f"; co {len(bad)} dong JSON hong" if bad else "")}
    prev = GENESIS
    for i, (no, r) in enumerate(rows):
        if r is None:
            return {**out, "status": "BROKEN", "bad_line": no, "entries": i, "head": None,
                    "reason": "dong khong phai JSON hop le"}
        if "entry_hash" not in r or "prev_hash" not in r:
            return {**out, "status": "BROKEN", "bad_line": no, "entries": i, "head": None,
                    "reason": "dong thieu prev_hash/entry_hash (bi chen hoac sua)"}
        if r["prev_hash"] != prev:
            return {**out, "status": "BROKEN", "bad_line": no, "entries": i, "head": None,
                    "reason": "prev_hash khong khop dong truoc (dong bi xoa, chen hoac dao thu tu)"}
        if entry_hash(r) != r["entry_hash"]:
            return {**out, "status": "BROKEN", "bad_line": no, "entries": i, "head": None,
                    "reason": "entry_hash khong khop noi dung (dong bi sua)"}
        prev = r["entry_hash"]
    return {**out, "entries": len(rows), "head": prev}


def verify_recent(limit=20, log_dir=None):
    """Kiem tra `limit` file log moi nhat (theo mtime). Tra ve danh sach ket qua."""
    d = Path(log_dir or config.LOG_DIR)
    if not d.exists():
        return []
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [verify_file(f) for f in files[:limit]]
