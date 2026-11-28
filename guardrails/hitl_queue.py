import json
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime

import config

QUEUE_PATH = config.ROOT / "experiments" / "results_raw" / "hitl_queue.jsonl"
TTL_SECONDS = 600


@contextmanager
def _locked_queue():
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_PATH.with_suffix(".lock").open("a+b") as lock:
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def _read_all():
    if not QUEUE_PATH.exists():
        return []
    return [
        json.loads(l)
        for l in QUEUE_PATH.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]


def _write_all(rows):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=QUEUE_PATH.parent,
                                     delete=False) as file:
        temporary = file.name
        try:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
            file.close()
            os.replace(temporary, QUEUE_PATH)
        finally:
            file.close()
            if os.path.exists(temporary):
                os.unlink(temporary)


def enqueue(tool, args, model=None, run_id=None, *, reason="", continuation=None):
    item = {
        "id": uuid.uuid4().hex,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "created_at": time.time(),
        "status": "pending",
        "model": model,
        "run_id": run_id,
        "tool": tool,
        "args": args,
        "reason": reason,
        "continuation": continuation,
    }
    with _locked_queue():
        rows = _read_all()
        rows.append(item)
        _write_all(rows)
    return item["id"]


def _expired(item):
    created = item.get("created_at")
    if created is None:
        created = datetime.fromisoformat(item["ts"]).timestamp()
    return time.time() - created >= TTL_SECONDS


def list_items(status=None):
    with _locked_queue():
        rows = _read_all()
        expired = [row for row in rows if row["status"] == "pending" and _expired(row)]
        for row in expired:
            _finish(row, "expired")
        if expired:
            _write_all(rows)
    for row in expired:
        _log_expired(row)
    for row in rows:
        saved = row.pop("continuation", None)
        row["can_approve"] = bool(saved and saved.get("layers") is not None)
        row["taint_source"] = saved["state"].get("taint_source") if saved else None
    return [row for row in rows if row["status"] == status] if status else rows


def _log_expired(row):
    """Yeu cau tu het han khi mo hang doi: ghi human_decision de nhat ky kiem toan thay duoc."""
    if not row.get("run_id"):
        return
    from experiments.logger import RunLogger
    RunLogger(row["model"], run_id=row["run_id"]).emit(
        "human_decision", tool=row["tool"], decision="EXPIRED", layer=4,
        reason="het han tu dong, khong ai xu ly", pending_id=row["id"])


def _finish(row, status):
    row["status"] = status
    row["resolved_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    row.pop("continuation", None)


def _find(rows, item_id):
    return next((row for row in rows if row["id"] == item_id), None)


def resolve(item_id, approve):
    from agent.core import resume_agent
    from experiments.logger import RunLogger

    out = {"status": "unavailable", "sent": False, "detail": ""}
    with _locked_queue():
        rows = _read_all()
        item = _find(rows, item_id)
        if item is None or item["status"] != "pending":
            return out
        saved = item.get("continuation")
        if _expired(item):
            status = "expired"
        elif not approve:
            status = "rejected"
        elif not saved or saved.get("layers") is None:
            return {**out, "detail": "Yeu cau cu khong co trang thai de tiep tuc."}
        else:
            status = "processing"
        _finish(item, status)
        _write_all(rows)

    out["status"] = status
    if item.get("run_id"):
        emit = RunLogger(item["model"], run_id=item["run_id"]).emit
        emit("human_decision", tool=item["tool"], decision="APPROVE" if status == "processing" else status.upper(),
             layer=4, pending_id=item_id)
    else:
        emit = lambda *args, **kwargs: None
    if status != "processing":
        return out

    try:
        output, result = resume_agent({**item, "continuation": saved}, emit)
        failed = isinstance(output, dict) and "error" in output
        out["status"] = "failed" if failed else "approved"
        out["sent"] = not failed and item["tool"] == "send_email"
        out["detail"] = str(output["error"])[:300] if failed else ""
        out["result"] = result
    except Exception as error:
        out["status"] = "failed"
        out["detail"] = str(error)[:300]
    finally:
        with _locked_queue():
            rows = _read_all()
            _finish(_find(rows, item_id), out["status"])
            _write_all(rows)
    return out
