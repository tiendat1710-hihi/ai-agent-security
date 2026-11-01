import json
import time
import uuid
from pathlib import Path

import config


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
                rows.append(json.loads(line))
    return rows


def list_runs(limit=20):
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(config.LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [f.stem for f in files[:limit]]