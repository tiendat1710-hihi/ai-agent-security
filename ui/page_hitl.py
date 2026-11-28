import streamlit as st
import requests
from guardrails import hitl_queue
from lab import leak_checker


def render(ctx):
    st.subheader("Hàng đợi duyệt — Human-in-the-Loop (Lớp 4)")
    st.caption(
        "Khi Lớp 4 bật, thư ngoài miền chờ duyệt. Khi bật thêm Lớp 2, truy vấn bảng nhạy cảm "
        "sau khi đọc email cũng có thể chờ duyệt. Yêu cầu hết hạn sau 10 phút."
    )

    flash = st.session_state.pop("hitl_flash", None)
    if flash:
        level, msg = flash
        getattr(st, level)(msg)

    pending = hitl_queue.list_items(status="pending")
    if not pending:
        st.success("Không có hành động nào đang chờ duyệt.")
        st.caption("Yêu cầu xuất hiện khi agent đề xuất một hành động cần duyệt.")
    else:
        st.warning(f"Có {len(pending)} hành động đang chờ duyệt.")
        for it in pending:
            args = it.get("args", {})
            st.divider()
            st.markdown(f"**{it['tool']}**  ·  id `{it['id']}`  ·  {it['ts']}  ·  {it.get('model', '')}")
            if it["tool"] == "send_email":
                st.text(f"Gửi tới: {args.get('to', '')}\nTiêu đề: {args.get('subject', '')}")
                st.text_area("Nội dung thư", args.get("body", ""), height=140,
                             key=f"body_{it['id']}", disabled=True)
                st.error("Người nhận ngoài miền công ty.")
            elif it["tool"] == "query_db":
                st.code(args.get("sql", ""), language="sql")
                st.error("Truy vấn dữ liệu cần duyệt.")
            if source := it.get("taint_source"):
                st.error("Kiểm tra nguồn email trước khi duyệt.")
                st.text(f"Từ: {source.get('from')}\nTiêu đề: {source.get('subject')}")
            if not it["can_approve"]:
                st.info("Yêu cầu cũ thiếu trạng thái để tiếp tục. Bạn có thể từ chối yêu cầu này.")

            c1, c2 = st.columns(2)
            if c1.button("Duyệt", key=f"ok_{it['id']}", type="primary", disabled=not it["can_approve"]):
                with st.spinner("Đang thực thi và tiếp tục lượt chạy…"):
                    out = hitl_queue.resolve(it["id"], approve=True)
                st.session_state["hitl_flash"] = _approval_message(out)
                st.rerun()

            if c2.button("Từ chối (chặn)", key=f"no_{it['id']}"):
                out = hitl_queue.resolve(it["id"], approve=False)
                message = ("Đã từ chối. Lượt chạy dừng tại hành động chờ duyệt."
                           if out["status"] == "rejected" else "Yêu cầu đã hết hạn hoặc đã được xử lý.")
                st.session_state["hitl_flash"] = ("info", message)
                st.rerun()

    with st.expander("Lịch sử đã xử lý"):
        done = [r for r in hitl_queue.list_items() if r["status"] != "pending"]
        if not done:
            st.text("Chưa có.")
        for r in reversed(done[-20:]):
            label = {"approved": "ĐÃ THỰC THI", "rejected": "TỪ CHỐI", "expired": "HẾT HẠN",
                     "processing": "ĐANG XỬ LÝ", "failed": "THỰC THI LỖI"}.get(r["status"], r["status"])
            a = r.get("args", {})
            st.text(f"[{label}] {r['id']} | {r['tool']} | {a.get('to', '')}")


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
    elif result["status"] == "infra_error":
        message += f" Phần tiếp tục gặp lỗi: {result['error']}"
    elif result["final"]:
        message += f" Kết quả: {result['final']}"
    return level, message
