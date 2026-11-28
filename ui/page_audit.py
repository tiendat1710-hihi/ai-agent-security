"""Nhat ky kiem toan: doc log .jsonl, loc theo lop / quyet dinh / mo hinh, thong ke.
Logic doc va dem nam o experiments/audit_summary.py (dung chung voi CLI)."""
import altair as alt
import pandas as pd
import streamlit as st

from experiments import audit_summary as au
from experiments.logger import read_run, verify_recent

DECISION_ORDER = ["ALLOW", "BLOCK", "PENDING_APPROVAL", "APPROVED", "REJECTED"]
# Trang thai dung mau trang thai (khong phai mau series), luon kem nhan chu.
DECISION_COLOR = {"ALLOW": "#0aa35c", "BLOCK": "#d92d20", "PENDING_APPROVAL": "#f2a600",
                  "APPROVED": "#257de0", "REJECTED": "#7a7a7a"}
LAYER_LABEL = {1: "L1", 2: "L2", 3: "L3", 4: "L4"}
STATUS_VN = {"OK": "✅ Nguyên vẹn", "BROKEN": "❌ Đứt chuỗi", "UNCHAINED": "⚪ Log cũ (chưa có chuỗi băm)",
             "EMPTY": "⚪ Rỗng"}


def _integrity_section():
    """Nut kiem tra chuoi prev_hash -> entry_hash cua cac file log gan nhat."""
    c1, c2 = st.columns([3, 1])
    with c2:
        limit = st.number_input("Số file gần nhất", min_value=1, max_value=500, value=20,
                                step=5, key="integrity_limit")
    with c1:
        clicked = st.button("Kiểm tra tính toàn vẹn Log (SHA-256)", key="integrity_check",
                            type="secondary")
    if not clicked:
        return
    res = verify_recent(int(limit))
    if not res:
        st.info("Không có file log nào để kiểm tra.")
        return
    broken = [r for r in res if r["status"] == "BROKEN"]
    legacy = [r for r in res if r["status"] == "UNCHAINED"]
    ok = [r for r in res if r["status"] == "OK"]
    if broken:
        st.error(f"Phát hiện {len(broken)}/{len(res)} file log bị đứt chuỗi băm: "
                 + ", ".join(f"{r['file']} (dòng {r['bad_line']})" for r in broken))
    else:
        st.success(f"{len(ok)}/{len(res)} file log nguyên vẹn: chuỗi prev_hash → entry_hash khớp "
                   f"trên {sum(r['entries'] for r in ok)} dòng.")
    if legacy:
        st.caption(f"{len(legacy)} file tạo trước khi có chuỗi băm nên không kiểm tra được.")
    df = pd.DataFrame(res)
    df["status"] = df["status"].map(STATUS_VN)
    df["head"] = df["head"].map(lambda h: f"{h[:16]}…" if isinstance(h, str) else "")  # NaN/None -> trong
    st.dataframe(df[["file", "status", "entries", "bad_line", "reason", "head"]].rename(columns={
        "file": "File", "status": "Trạng thái", "entries": "Số dòng hợp lệ", "bad_line": "Dòng lỗi",
        "reason": "Lý do", "head": "Băm cuối chuỗi"}), hide_index=True, use_container_width=True)
    st.caption("Phát hiện sửa/xóa/chèn/đảo dòng. Không phát hiện: cắt bỏ các dòng cuối file, "
               "hoặc người có quyền ghi tính lại toàn bộ chuỗi (chưa dùng khóa bí mật).")


def _card(title, sub):
    st.markdown(
        f'<div class="ui-card"><div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">'
        f'{title}</div><div style="color:#6E6E73; font-size:0.88rem;">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def render(ctx):
    _card("Nhật ký kiểm toán",
          "Mọi quyết định của Guardrails (L1–L4) và của người duyệt, đọc từ "
          "<code>experiments/results_raw/logs/*.jsonl</code>.")

    _integrity_section()

    rows = au.load_rows()
    decs = au.decisions(rows)
    if not decs:
        st.info("Chưa có quyết định nào trong log. Chạy agent với ít nhất một lớp phòng thủ bật.")
        return

    f1, f2, f3 = st.columns([2, 3, 2])
    with f1:
        layer_names = st.multiselect("Lớp", ["L1", "L2", "L3", "L4", "-"],
                                     default=["L1", "L2", "L3", "L4", "-"], key="audit_layers",
                                     help="'-' = ALLOW không gắn lớp nào (policy cho qua)")
    with f2:
        dec_sel = st.multiselect("Quyết định", DECISION_ORDER, default=DECISION_ORDER,
                                 key="audit_decisions",
                                 help="APPROVED / REJECTED là sự kiện human_decision của Lớp 4")
    with f3:
        models = sorted({d["model"] for d in decs if d["model"]})
        model_sel = st.multiselect("Mô hình", models, default=models, key="audit_models")

    layers = {None if n == "-" else int(n[1]) for n in layer_names}
    shown = au.filter_decisions(decs, layers=layers, decisions_=set(dec_sel),
                                models=set(model_sel))
    s = au.summarize(shown)

    m1, m2, m3, m4, m5 = st.columns(5)
    count = {k: sum(n for (d, _), n in s["by_decision_layer"].items() if d == k)
             for k in ("ALLOW", "BLOCK", "PENDING_APPROVAL")}
    m1.metric("Quyết định", s["total"])
    m2.metric("BLOCK", count["BLOCK"])
    m3.metric("PENDING_APPROVAL", count["PENDING_APPROVAL"])
    m4.metric("Duyệt / Từ chối", f'{s["human"]["approved"]} / {s["human"]["rejected"]}')
    m5.metric("Hết hạn", s["human"]["expired"])

    if not shown:
        st.warning("Không có quyết định nào khớp bộ lọc.")
        return

    df = pd.DataFrame(shown)
    df["lop"] = df["layer"].map(LAYER_LABEL).fillna("-")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("**Số quyết định theo lớp**")
        agg = df.groupby(["lop", "decision"]).size().reset_index(name="so_luong")
        order = [d for d in DECISION_ORDER if d in set(agg["decision"])]
        chart = (
            alt.Chart(agg)
            .mark_bar(cornerRadiusEnd=4, size=18)
            .encode(
                y=alt.Y("lop:N", title=None, sort=["L1", "L2", "L3", "L4", "-"]),
                x=alt.X("so_luong:Q", title="Số quyết định", stack="zero",
                        axis=alt.Axis(tickMinStep=1, format="d")),
                color=alt.Color("decision:N", title="Quyết định",
                                scale=alt.Scale(domain=order,
                                                range=[DECISION_COLOR[d] for d in order])),
                order=alt.Order("decision:N"),
                tooltip=[alt.Tooltip("lop:N", title="Lớp"),
                         alt.Tooltip("decision:N", title="Quyết định"),
                         alt.Tooltip("so_luong:Q", title="Số lượng")],
            )
            .properties(height=60 + 34 * agg["lop"].nunique())
            .configure_axis(grid=False, domainColor="#d0d0d5")
            .configure_view(stroke=None)
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(agg.pivot_table(index="lop", columns="decision", values="so_luong",
                                     fill_value=0), use_container_width=True)
    with c2:
        st.markdown("**Top lý do chặn / treo**")
        if s["top_reasons"]:
            st.dataframe(pd.DataFrame(s["top_reasons"], columns=["Lý do", "Số lần"]),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("Không có lần chặn/treo nào trong bộ lọc.")
        st.markdown("**Theo luật**")
        if s["top_rules"]:
            st.dataframe(pd.DataFrame(s["top_rules"], columns=["Luật", "Số lần"]),
                         hide_index=True, use_container_width=True)

    st.markdown("**Chi tiết quyết định**")
    cols = ["ts", "run_id", "model", "lop", "tool", "decision", "rule", "reason", "reviewer"]
    st.dataframe(df.sort_values("ts", ascending=False)[cols], hide_index=True,
                 use_container_width=True, height=320)

    runs = list(dict.fromkeys(df.sort_values("ts", ascending=False)["run_id"]))
    run = st.selectbox("Xem toàn bộ dòng thời gian của một phiên", runs, key="audit_run")
    if run:
        tl = pd.DataFrame(read_run(run))
        keep = [c for c in ["ts", "event", "tool", "decision", "layer", "rule", "reason",
                            "result_preview", "pending_id", "reviewer"] if c in tl.columns]
        st.dataframe(tl[keep], hide_index=True, use_container_width=True)
