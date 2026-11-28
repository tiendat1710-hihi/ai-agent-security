from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from experiments.audit_summary import read_audit
from ui.common import metric_cards, section_header

DECISIONS = {
    "ALLOW": ("Cho phép", "#087a65"),
    "BLOCK": ("Chặn", "#bd4058"),
    "PENDING_APPROVAL": ("Chờ duyệt", "#bd7719"),
    "APPROVED": ("Đã duyệt", "#3857b6"),
    "REJECTED": ("Từ chối", "#7652a8"),
    "EXPIRED": ("Hết hạn", "#63728b"),
    "INFRA_ERROR": ("Lỗi hạ tầng", "#38445c"),
}
LAYERS = ["L1", "L2", "L3", "L4", "—"]


def decision_label(value):
    return DECISIONS.get(value, (value, ""))[0]


def render(ctx):
    section_header("Nhật ký kiểm toán", "Tra quyết định phòng thủ theo mô hình, lớp và mã lượt chạy.")
    rows, skipped = read_audit()
    if skipped:
        st.warning(f"Bỏ qua {skipped} dòng hoặc tệp nhật ký không đọc được.")
    if not rows:
        st.info("Chưa có sự kiện kiểm toán. Chạy một yêu cầu hoặc xử lý một mục chờ duyệt để tạo nhật ký.")
        return

    with st.container(border=True, key="audit_filters"):
        filters = st.columns((1, 1.4, 1.3))
        layers = filters[0].multiselect("Lớp", [name for name in LAYERS if any(r["layer"] == name for r in rows)],
                                        placeholder="Tất cả lớp")
        options = list(dict.fromkeys([*DECISIONS, *(r["decision"] for r in rows)]))
        decisions = filters[1].multiselect("Quyết định", options, format_func=decision_label,
                                            placeholder="Tất cả quyết định")
        models = filters[2].multiselect("Mô hình", sorted({str(r["model"]) for r in rows if r.get("model")}),
                                         placeholder="Tất cả mô hình")
        run_id = st.text_input("Mã lượt chạy", placeholder="Nhập toàn bộ hoặc một phần mã lượt")

    matches = [r for r in rows if (not layers or r["layer"] in layers)
               and (not decisions or r["decision"] in decisions)
               and (not models or r.get("model") in models)
               and run_id.strip().lower() in r["run_id"].lower()]
    if not matches:
        st.info("Không có sự kiện khớp với bộ lọc.")
        return

    counts = Counter(r["decision"] for r in matches)
    metric_cards([
        ("Sự kiện", len(matches), f"{len({r['run_id'] for r in matches})} lượt chạy"),
        ("Chặn", counts["BLOCK"], "Quyết định của Guardrails"),
        ("Yêu cầu duyệt", counts["PENDING_APPROVAL"], "Số lần được đưa vào hàng đợi"),
        ("Từ người duyệt", counts["APPROVED"] + counts["REJECTED"],
         f"{counts['APPROVED']} duyệt · {counts['REJECTED']} từ chối"),
    ])

    chart_col, reasons_col = st.columns((3, 2))
    with chart_col, st.container(border=True, key="audit_chart"):
        st.markdown("#### Quyết định theo lớp")
        grouped = Counter((r["layer"], r["decision"]) for r in matches)
        data = pd.DataFrame([{"Lớp": layer, "Quyết định": decision_label(decision), "Số sự kiện": count}
                             for (layer, decision), count in grouped.items()])
        colors = alt.Scale(domain=[label for label, _ in DECISIONS.values()],
                           range=[color for _, color in DECISIONS.values()])
        chart = alt.Chart(data).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("Số sự kiện:Q", axis=alt.Axis(tickMinStep=1), title=None),
            y=alt.Y("Lớp:N", sort=LAYERS, title=None),
            color=alt.Color("Quyết định:N", scale=colors, legend=None),
            tooltip=["Lớp:N", "Quyết định:N", "Số sự kiện:Q"],
        ).properties(height=190)
        st.altair_chart(chart, width="stretch")
        st.caption(" · ".join(decision_label(code) for code in DECISIONS if counts[code]))

    with reasons_col, st.container(border=True, key="audit_reasons"):
        st.markdown("#### Lý do chặn và chờ duyệt")
        reasons = Counter(str(r["reason"]) for r in matches
                          if r.get("reason") and r["decision"] in {"BLOCK", "PENDING_APPROVAL"})
        if reasons:
            for reason, count in reasons.most_common(4):
                st.text(f"{count} lần · {reason}", width="stretch")
        else:
            st.caption("Chưa ghi nhận lý do trong bộ lọc này.")
        rules = Counter(str(r["rule"]) for r in matches if r.get("rule"))
        if rules:
            with st.expander("Quy tắc được ghi nhận"):
                st.dataframe(pd.DataFrame(rules.most_common(), columns=["Quy tắc", "Số lần"]),
                             hide_index=True, width="stretch")

    with st.container(border=True, key="audit_events"):
        st.markdown("#### Sự kiện gần đây")
        recent = matches[:200]
        table = pd.DataFrame([{
            "Thời điểm": row.get("ts"),
            "Mã lượt": row["run_id"],
            "Mô hình": row.get("model"),
            "Lớp": row["layer"],
            "Quyết định": decision_label(row["decision"]),
            "Công cụ": row.get("tool"),
            "Lý do": row.get("reason"),
        } for row in recent])
        st.dataframe(table, hide_index=True, width="stretch", height=300)
        if len(recent) < len(matches):
            st.caption("Hiển thị 200 sự kiện gần nhất. Dùng mã lượt chạy để tra sâu hơn.")
