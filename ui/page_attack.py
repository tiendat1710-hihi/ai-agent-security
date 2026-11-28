import streamlit as st
import config
from agent import core
from experiments.logger import RunLogger
from experiments.measure_asr import VICTIM_TASK, load_attacks
from lab import leak_checker, mail_client

TECH_VN = {
    "direct_override": "Ghi đè trực tiếp (ignore all previous instructions)",
    "impersonation": "Giả danh quản trị (admin/IT)",
    "urgency": "Tạo gấp gáp / đe dọa",
    "hidden_instruction": "Chỉ dẫn ẩn trong HTML (display:none)",
    "fake_system_format": "Giả định dạng thông báo hệ thống",
    "split_instruction": "Chia nhỏ chỉ dẫn qua 2 email",
}


def _deliver(atk):
    mail_client.clear_mailbox(config.INTERNAL_MAIL)
    mail_client.clear_mailbox(config.EXTERNAL_MAIL)
    for e in atk["emails"]:  # nạp theo thứ tự, email cuối = mới nhất
        mail_client.deliver_to_inbox(
            e["from"], e["subject"], e["body_text"], e.get("body_html")
        )


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.05rem; margin-bottom:4px;">
                Tấn công trực tiếp — Indirect Prompt Injection
            </div>
            <div style="color:#6E6E73; font-size:0.9rem;">
                Email tấn công giả làm thư công việc bình thường nhưng nhúng chỉ dẫn độc hại.
                Agent đọc email là bị "nhiễm". Bật/tắt các lớp ở thanh bên trái để đối chiếu.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    attacks = load_attacks()
    if not attacks:
        st.warning("Không có payload trong attacks/seeds/.")
        return

    labels = {
        a["id"]: f"{a['id']}  —  {TECH_VN.get(a['group'], a['group'])}"
        for a in attacks
    }
    chosen = st.selectbox(
        "Chọn kịch bản tấn công",
        list(labels),
        format_func=lambda i: labels[i],
    )
    atk = next(a for a in attacks if a["id"] == chosen)

    st.markdown("**Nội dung email sẽ nạp vào hộp thư nạn nhân:**")
    for e in atk["emails"]:
        with st.expander(f"Từ {e['from']}  |  {e['subject']}", expanded=True):
            st.code(e["body_text"], language=None)
            if e.get("body_html"):
                st.caption("Email này có chứa mã HTML ẩn (display:none) — dùng để kiểm chứng Lớp 1.")

    active_list = sorted(ctx["layers"])
    if active_list:
        defense_badge = f'<span class="pill pill-blue">Phòng thủ: {", ".join(active_list)}</span>'
    else:
        defense_badge = '<span class="pill pill-red">Phòng thủ: KHÔNG (none)</span>'

    st.markdown(
        f"""
        <div class="ui-card" style="padding:14px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div class="pill-group">
                <span class="pill pill-gray">Mô hình: {ctx['model']}</span>
                {defense_badge}
            </div>
            <div style="color:#6E6E73; font-size:0.85rem;">
                Tác vụ nạn nhân: <i>"{VICTIM_TASK}"</i>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Nạp email & chạy tấn công", type="primary"):
        _deliver(atk)
        log = RunLogger(ctx["model"])
        events = []

        def emit(event, **kw):
            log.emit(event, **kw)
            events.append({"event": event, **kw})

        with st.spinner(f"{ctx['model']} đang đọc email và hành động..."):
            res = core.run_agent(
                VICTIM_TASK,
                model=ctx["model"],
                policy=ctx["policy"],
                emit=emit,
                run_id=log.run_id,
                on_pending="pause",   # L4: dung vong lap, luu checkpoint cho tab HITL
            )

        st.markdown("### Diễn biến thực thi (Plan → Act → Observe)")
        for ev in events:
            e = ev["event"]
            if e == "guardrail_decision":
                d, layer, reason = ev.get("decision"), ev.get("layer"), ev.get("reason")
                if d == "BLOCK":
                    st.error(f"🛡️ Lớp {layer} CHẶN `{ev.get('tool')}` — {reason}")
                elif d == "PENDING_APPROVAL":
                    st.warning(
                        f"⏸️ Lớp {layer} TREO DUYỆT `{ev.get('tool')}` — {reason}. "
                        f"Vòng lặp đã tạm dừng, chờ duyệt ở tab Hàng đợi duyệt"
                    )
            elif e == "tool_call":
                st.markdown(f"➡️ Gọi công cụ **`{ev.get('tool')}`**")
                if ev.get("args"):
                    st.caption("args: " + str(ev.get("args"))[:300])
            elif e == "tool_result":
                st.caption("↳ kết quả: " + (ev.get("result_preview") or "")[:300])
            elif e == "final_answer":
                st.success("✅ Trả lời cuối: " + (ev.get("result_preview") or ""))

        st.markdown("### Phán quyết của trọng tài (leak_checker)")
        ext = leak_checker.check_external()
        tools_used = [c["tool"] for c in res.get("tool_calls", [])]
        if tools_used:
            pills = " ".join(f'<span class="pill pill-gray">{t}</span>' for t in tools_used)
            st.markdown(
                f'<div class="pill-group" style="margin-bottom:8px;">'
                f'<span style="font-size:0.85rem; color:#6E6E73;">Chuỗi công cụ:</span>{pills}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Chuỗi công cụ: (không gọi công cụ nào)")

        if ext["leaked"]:
            st.markdown(
                f'<div class="verdict-box verdict-leak">'
                f'<strong>❌ TẤN CÔNG THÀNH CÔNG — RÒ RỈ THẬT:</strong> '
                f'Phát hiện <b>{ext["distinct_markers"]}</b> marker thật lọt ra hộp thư ngoài.'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif ext["messages"]:
            st.markdown(
                f'<div class="verdict-box verdict-warn">'
                f'<strong>⚠️ CÓ THƯ GỬI RA NGOÀI:</strong> Có <b>{ext["messages"]}</b> thư gửi ra ngoài '
                f'nhưng CHƯA thấy marker thật (dữ liệu giả lập, chưa phải rò rỉ thật).'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="verdict-box verdict-safe">'
                '<strong>✅ PHÒNG THỦ GIỮ VỮNG:</strong> Không có dữ liệu hay email nào lọt ra hộp thư ngoài.'
                '</div>',
                unsafe_allow_html=True,
            )

        with st.expander("Hộp thư BÊN NGOÀI (hacker) sau lượt chạy", expanded=bool(ext["messages"])):
            msgs = mail_client.list_messages(config.EXTERNAL_MAIL)[:10]
            if not msgs:
                st.text("Trống.")
            for m in msgs:
                st.text(f"{m['from']} -> {m['to']} | {m['subject']}")