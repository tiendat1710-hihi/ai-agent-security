import requests
import streamlit as st

from guardrails import hitl_queue
from lab import leak_checker
from ui.common import metric_cards, section_header

STATUS_LABELS = {
    "approved": "Đã thực thi",
    "rejected": "Từ chối",
    "expired": "Hết hạn",
    "processing": "Đang xử lý",
    "failed": "Thực thi lỗi",
}
TOOL_LABELS = {"send_email": "Gửi thư ngoài miền", "query_db": "Truy vấn dữ liệu"}


def render(ctx):
    section_header("Hàng đợi duyệt", "Xem đề xuất của agent trước khi quyết định thực thi.")
    if flash := st.session_state.pop("hitl_flash", None):
        level, message = flash
        getattr(st, level)(message)

    items = hitl_queue.list_items()
    pending = [item for item in reversed(items) if item["status"] == "pending"]
    history = [item for item in reversed(items) if item["status"] != "pending"]
    timeout_minutes = hitl_queue.TTL_SECONDS // 60
    metric_cards([
        ("Chờ duyệt", len(pending), f"Hết hạn sau {timeout_minutes} phút"),
        ("Đang thực thi", sum(item["status"] == "processing" for item in history), "Yêu cầu đang được xử lý"),
        ("Đã xử lý", sum(item["status"] != "processing" for item in history), "Xem chi tiết trong lịch sử"),
    ])
    if "L4" not in ctx["layers"]:
        st.caption("L4 đang tắt cho lượt mới. Các yêu cầu đang chờ vẫn dùng cấu hình gốc.")
    if not pending:
        st.info("Không có yêu cầu chờ duyệt.")

    for item in pending:
        with st.container(border=True, key=f"hitl_request_{item['id']}"):
            _render_request(item)

    with st.expander("Lịch sử xử lý"):
        if not history:
            st.caption("Chưa có yêu cầu đã xử lý.")
        else:
            st.dataframe([{
                "Thời điểm": item.get("resolved_ts") or item["ts"],
                "Hành động": TOOL_LABELS.get(item["tool"], item["tool"]),
                "Trạng thái": STATUS_LABELS.get(item["status"], item["status"]),
                "Mã lượt": item.get("run_id"),
                "Mã yêu cầu": item["id"],
            } for item in history[:30]], hide_index=True, width="stretch")


def _render_request(item):
    args = item["args"]
    tool = item["tool"]
    st.markdown(f"#### {TOOL_LABELS.get(tool, 'Hành động cần duyệt')}")
    if tool == "send_email":
        st.text(f"Người nhận  {args.get('to', '')}\nTiêu đề thư gửi  {args.get('subject', '')}")
        st.code(args.get("body", ""), language=None, wrap_lines=True)
    elif tool == "query_db":
        st.code(args.get("sql", ""), language="sql", wrap_lines=True)

    with st.expander("Chi tiết yêu cầu"):
        st.text(f"Mô hình  {item.get('model') or '—'}\nTạo lúc  {item['ts']}\n"
                f"Mã lượt  {item.get('run_id') or '—'}\nMã yêu cầu  {item['id']}")
        if item.get("reason"):
            st.text(f"Lý do  {item['reason']}")

    if not item["can_approve"]:
        st.info("Yêu cầu cũ thiếu trạng thái để tiếp tục. Bạn có thể từ chối yêu cầu này.")

    if source := item.get("taint_source"):
        with st.container(border=True, key=f"hitl_taint_{item['id']}"):
            st.error("Đề xuất này xuất hiện sau khi agent đọc email bên dưới. Email có thể chứa chỉ thị "
                     "của kẻ tấn công, và địa chỉ người gửi có thể bị giả mạo.")
            st.text(f"Người gửi  {source.get('from') or '—'}\nTiêu đề email nguồn  {source.get('subject') or '—'}")

    reject, approve = st.columns(2)
    if reject.button("Từ chối", key=f"no_{item['id']}", width="stretch"):
        out = hitl_queue.resolve(item["id"], approve=False)
        message = ("Đã từ chối. Lượt chạy dừng tại hành động chờ duyệt."
                   if out["status"] == "rejected" else "Yêu cầu đã hết hạn hoặc đã được xử lý.")
        st.session_state["hitl_flash"] = ("info", message)
        st.rerun()
    if approve.button("Duyệt", key=f"ok_{item['id']}", type="primary",
                      width="stretch", disabled=not item["can_approve"]):
        with st.spinner("Đang thực thi và tiếp tục lượt chạy…"):
            out = hitl_queue.resolve(item["id"], approve=True)
        st.session_state["hitl_flash"] = _approval_message(out)
        st.rerun()


def _approval_message(out):
    if out["status"] == "failed":
        return "error", f"Thực thi sau duyệt thất bại. {out['detail']}"
    if out["status"] != "approved":
        return "warning", "Yêu cầu đã hết hạn hoặc đã được xử lý."

    result = out["result"]
    level, message = "success", "Đã gửi thư." if out["sent"] else "Đã chạy truy vấn được duyệt."
    if out["sent"]:
        try:
            ext = leak_checker.check_external()
        except (requests.RequestException, OSError):
            level, message = "warning", message + " Chưa kiểm tra được hộp thư ngoài."
        else:
            if ext["leaked"]:
                level = "error"
                message += f" Hộp thư ngoài hiện có {ext['distinct_markers']} marker dữ liệu nhạy cảm."
    if result["status"] == "pending":
        message += f" Agent đang chờ duyệt yêu cầu tiếp theo {result['pending_id']}."
    elif result["status"] == "max_steps":
        message += " Agent hết số bước trước khi trả lời."
    elif result["status"] == "output_truncated":
        message += " Phần tiếp tục dừng vì model chạm giới hạn đầu ra."
    elif result["status"] == "infra_error":
        message += f" Phần tiếp tục gặp lỗi: {result['error']}"
    elif result["final"]:
        message += f" Kết quả: {result['final']}"
    return level, message
