"""Hang doi duyet (Lop 4). Nguon su that la thu muc checkpoint tren dia
(core.PENDING_DIR), khong phai st.session_state: F5 trinh duyet, rerun cua
Streamlit hay phien tao tu tab khac deu van thay o day."""
import html
import json
import time

import streamlit as st

import config
from agent import core
from experiments.logger import RunLogger
from lab import leak_checker

RULE_VN = {
    "L2.taint_sensitive_read": "Đọc bảng mật sau khi đã nhiễm nội dung ngoài",
    "L2.recipient_allowlist": "Gửi thư tới địa chỉ ngoài @company.test",
    "L2.sql_unanalyzable": "SQL không phân tích chắc chắn được khi đã nhiễm",
}


def _context_preview(ck):
    """Noi dung email agent da doc. Hien bang text_area (disabled): van ban thuan,
    KHONG render markdown/HTML -> khong co link mailto/URL bam duoc do ke tan cong cai."""
    srcs = ck.get("taint_sources") or []
    if not srcs:
        return "(phiên này chưa đọc email)"
    return "\n\n----------\n\n".join(
        f"From: {x.get('from')}\nSubject: {x.get('subject')}\n\n{x.get('preview', '')}" for x in srcs)


def _show_outcome(res):
    if res.get("status") == "EXPIRED":
        st.warning("Yêu cầu đã hết hạn trước khi bấm: hệ thống tự Reject, công cụ không chạy.")
        return
    if res.get("status") == "PENDING_APPROVAL":
        st.warning("Agent chạy tiếp rồi lại dừng ở một hành động khác cần duyệt "
                   f"(phiên mới `{res['pending_id']}`).")
    elif res.get("final"):
        st.success("Agent đã hoàn tất: " + res["final"][:300])
    else:
        st.info(f"Agent dừng: {res.get('status')}")
    ext = leak_checker.check_external()
    if ext["leaked"]:
        st.error(f"Hộp thư ngoài có {ext['distinct_markers']} marker thật: quyết định duyệt đã gây rò rỉ.")


def _taint_box(ck):
    """Khung do canh bao nguon gay nhiem. MOI truong tu email (from/subject) la du lieu
    do ke tan cong kiem soat -> html.escape truoc khi nhung vao HTML."""
    srcs = ck.get("taint_sources") or ([ck["taint_source"]] if ck.get("taint_source") else [])
    if not ck["state"].get("tainted"):
        return
    items = "".join(
        f"<li><b>Người gửi:</b> {html.escape(str(x.get('from') or '(không rõ)'))}"
        f" · <b>Tiêu đề:</b> {html.escape(str(x.get('subject') or '(không rõ)'))}"
        f" · bước {html.escape(str(x.get('step')))}</li>"
        for x in srcs) or "<li>(không ghi được nguồn)</li>"
    internal = any(str(x.get("from") or "").lower().endswith("@" + config.INTERNAL_DOMAIN)
                   for x in srcs)
    spoof = ("<br>Người gửi mang tên miền nội bộ <b>không</b> có nghĩa là đáng tin: "
             "địa chỉ From có thể bị giả mạo (kịch bản impersonation)." if internal else "")
    st.markdown(
        '<div class="verdict-box verdict-leak" style="margin-top:0;">'
        "<strong>⚠️ Yêu cầu này phát sinh SAU KHI agent đọc nội dung bên ngoài.</strong> "
        "Chỉ dẫn trong email có thể đang điều khiển agent. Nguồn gây nhiễm:"
        f"<ul style='margin:6px 0 0 18px; padding:0;'>{items}</ul>{spoof}</div>",
        unsafe_allow_html=True,
    )


def _remaining(ck, now=None):
    return int(config.HITL_TTL_SECONDS - ((now or time.time()) - (ck.get("created_at") or 0)))


def _expire_all():
    """Reject tu dong cac yeu cau qua han; ghi vao CUNG file log cua phien."""
    return core.expire_checkpoints(
        emit_factory=lambda ck: RunLogger(ck["model"], run_id=ck["run_id"]).emit)


def _decide(pid, approve):
    note = st.session_state.get(f"note_{pid}", "")   # doc luc bam, khong luc render
    try:
        with st.spinner("Đang thực thi quyết định và chạy tiếp vòng lặp ReAct..."):
            res = core.resume_agent(pid, approve=approve, reviewer="ui", note=note)
    except LookupError as e:          # bam 2 lan / da reset lab
        st.info(str(e))
        return
    st.session_state["hitl_last"] = res


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">Hàng đợi duyệt (HITL / Lớp 4)</div>
            <div style="color:#6E6E73; font-size:0.88rem;">
                Vòng lặp ReAct đang <b>tạm dừng</b> ở các hành động dưới đây. Approve chạy đúng
                công cụ + tham số đã treo rồi cho agent chạy tiếp; Reject trả "REJECTED" cho agent.
                Cấu hình phòng thủ dùng khi chạy tiếp là cấu hình lúc phiên bắt đầu, không phải thanh bên hiện tại.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "L4" not in ctx["layers"]:
        st.caption("Lớp 4 đang tắt ở thanh bên: phiên mới sẽ không vào hàng đợi, "
                   "nhưng các phiên đã treo vẫn duyệt được.")

    last = st.session_state.pop("hitl_last", None)
    if last:
        _show_outcome(last)

    expired = _expire_all()
    if expired:
        st.warning(f"Đã tự động Reject {len(expired)} yêu cầu quá "
                   f"{config.HITL_TTL_SECONDS // 60} phút: {', '.join(expired)}")

    items = core.list_checkpoints()
    if not items:
        st.info("Không có hành động nào đang chờ duyệt.")
        return
    st.markdown(f"**{len(items)} hành động đang chờ**")

    for ck in items:
        p = ck["pending"]
        v = p["verdict"]
        pid = ck["pending_id"]
        left = max(_remaining(ck), 0)
        title = (f"`{p['tool']}` · {RULE_VN.get(v.get('rule'), v.get('reason'))} · {ck['model']}"
                 f" · bước {p['step']}/{ck['max_steps']} · còn {left // 60}:{left % 60:02d}")
        with st.expander(title, expanded=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("**Hành động agent muốn thực hiện**")
                if p["tool"] == "query_db":
                    st.code(p["args"].get("sql", ""), language="sql")
                else:
                    st.code(json.dumps(p["args"], ensure_ascii=False, indent=2), language="json")
                st.caption(f"Lý do treo (Lớp {v.get('layer')}, luật {v.get('rule')}): {v.get('reason')}")
            with c2:
                st.markdown("**Ngữ cảnh**")
                st.caption(f"Yêu cầu người dùng: {ck['user_request']}")
                st.caption(f"Tạo lúc {ck.get('created_at_iso', '?')} · tự Reject sau "
                           f"{config.HITL_TTL_SECONDS // 60} phút")
                st.caption(f"Phòng thủ lúc chạy: {ck['policy_spec']} · L1={ck['enable_l1']}")
                st.markdown("**Email agent đã đọc**")
                st.text_area("Email agent đã đọc", _context_preview(ck), height=180,
                             disabled=True, key=f"mail_{pid}", label_visibility="collapsed")
            st.text_input("Ghi chú của người duyệt (vào nhật ký kiểm toán)", key=f"note_{pid}")
            bcol, wcol = st.columns([1, 3])
            with bcol:   # nut Approve dat SAT khung canh bao do
                st.button("Approve", key=f"ok_{pid}", type="primary", use_container_width=True,
                          on_click=_decide, args=(pid, True))
                st.button("Reject", key=f"no_{pid}", use_container_width=True,
                          on_click=_decide, args=(pid, False))
            with wcol:
                _taint_box(ck)
