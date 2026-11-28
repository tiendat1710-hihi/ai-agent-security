"""Bang ket qua: ma tran ASR (action / leak) theo lop phong thu + Utility Drop.
Nguon: experiments/results_raw/matrix_asr_action.csv, matrix_asr_leak.csv (do
build_matrix.py sinh) va utility_*.csv (moi cau hinh lay file moi nhat)."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from experiments import build_matrix as bm

# Bang mau phan loai co dinh theo THU TU mo hinh (khong xoay vong), da qua validator.
SERIES = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17"]
CFG_VN = {"none": "Không phòng thủ", "L1": "Chỉ L1", "L2": "Chỉ L2", "L3": "Chỉ L3",
          "L4": "Chỉ L4", "all": "Đủ 4 lớp", "hitlok-all": "Đủ 4 lớp + người duyệt"}


def _card(title, sub):
    st.markdown(
        f'<div class="ui-card"><div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">'
        f'{title}</div><div style="color:#6E6E73; font-size:0.88rem;">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def _model_scale(models):
    return alt.Scale(domain=list(models), range=SERIES[:len(models)])


def _bars(df, x, x_title, y_title, models, y_max=100):
    """Cot nhom: truc x = cau hinh, mau = mo hinh; 1 truc y duy nhat (0-100%)."""
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", title=None, sort=list(dict.fromkeys(df[x])),
                axis=alt.Axis(labelAngle=0, labelLimit=220)),
        xOffset=alt.XOffset("model:N", sort=list(models)),
        y=alt.Y("value:Q", title=y_title, scale=alt.Scale(domain=[0, y_max])),
        color=alt.Color("model:N", title="Mô hình", scale=_model_scale(models),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip(f"{x}:N", title=x_title), alt.Tooltip("model:N", title="Mô hình"),
                 alt.Tooltip("value:Q", title=y_title, format=".1f")],
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke="#ffffff",
                         strokeWidth=2)
    # Cot 0% khong co chieu cao -> ghi so "0" de khong lan voi o chua do (o trong).
    zeros = base.transform_filter("datum.value == 0").mark_text(
        dy=-6, fontSize=11).encode(text=alt.value("0"), color=alt.value("#6E6E73"))
    return (
        alt.layer(bars, zeros)
        .properties(height=280)
        .configure_axis(gridColor="#ececf0", domainColor="#d0d0d5")
        .configure_view(stroke=None)
    )


def _matrix_section(title, path, key):
    cols, rows = bm.read_matrix(path)
    st.markdown(f"#### {title}")
    if not rows:
        st.info(f"Chưa có `{Path(path).name}`. Chạy `python -m experiments.build_matrix` trước.")
        return None
    df = pd.DataFrame(rows)
    models = list(dict.fromkeys(df["model"]))
    long = df.melt(id_vars=["model", "ky_thuat"], value_vars=cols,
                   var_name="cau_hinh", value_name="value").dropna(subset=["value"])
    avg = long.groupby(["cau_hinh", "model"], sort=False)["value"].mean().reset_index()
    avg["cau_hinh"] = pd.Categorical(avg["cau_hinh"], categories=cols, ordered=True)
    avg = avg.sort_values(["cau_hinh", "model"])
    avg["cau_hinh"] = avg["cau_hinh"].astype(str)
    st.altair_chart(_bars(avg, "cau_hinh", "Cấu hình", "ASR trung bình (%)", models),
                    use_container_width=True)
    pick = st.selectbox("Bảng chi tiết theo mô hình", models, key=f"{key}_model")
    st.dataframe(df[df["model"] == pick].drop(columns="model").set_index("ky_thuat"),
                 use_container_width=True)
    return avg


def render(ctx):
    _card("Bảng kết quả",
          "Ma trận Defense-in-Depth (ASR-ACTION / ASR-LEAK, %) và Utility Drop trên 30 tác vụ "
          "hợp lệ. Mỗi cấu hình lấy file kết quả mới nhất trong <code>experiments/results_raw/</code>.")

    raw = Path(bm.RAW)
    t1, t2, t3 = st.tabs(["ASR-ACTION", "ASR-LEAK", "Utility Drop"])
    with t1:
        st.caption("% lượt agent bị điều khiển gửi thư ra ngoài.")
        _matrix_section("ASR-ACTION theo cấu hình", raw / "matrix_asr_action.csv", "act")
    with t2:
        st.caption("% lượt dữ liệu mật thật xuất hiện trong thư gửi ra ngoài.")
        _matrix_section("ASR-LEAK theo cấu hình", raw / "matrix_asr_leak.csv", "leak")
    with t3:
        ut = bm.utility_rows(raw)
        if not ut:
            st.info("Chưa có `utility_*.csv`. Chạy `python -m experiments.bench_baseline --defense ...`.")
            return
        df = pd.DataFrame(ut)
        models = list(dict.fromkeys(df["model"]))
        df["Cấu hình"] = df["config"].map(lambda c: CFG_VN.get(c, c))
        plot = df.rename(columns={"rate": "value"})
        st.altair_chart(_bars(plot, "Cấu hình", "Cấu hình", "Hoàn thành tác vụ (%)", models),
                        use_container_width=True)

        tot = df.groupby("config", sort=False)[["done", "total"]].sum().reset_index()
        tot["rate"] = (100 * tot["done"] / tot["total"]).round(1)
        base = tot.loc[tot["config"] == "none", "rate"]
        if len(base):
            tot["drop_vs_none"] = (base.iloc[0] - tot["rate"]).round(1)
            others = [r for r in tot.itertuples() if r.config != "none"]
            cols = st.columns(max(min(len(others), 4), 1))
            for i, r in enumerate(others):
                change = round(-r.drop_vs_none, 1) + 0.0          # +0.0: bo "-0.0"
                with cols[i % len(cols)]:
                    st.metric(CFG_VN.get(r.config, r.config), f"{r.done}/{r.total} ({r.rate}%)",
                              delta=None if change == 0 else f"{change:+.1f} điểm % so với none")
                    if change == 0:
                        st.caption("Không đổi so với none")
        st.markdown("**Tổng hợp**")
        st.dataframe(tot.rename(columns={"config": "Cấu hình", "done": "Đạt", "total": "Tổng",
                                         "rate": "Tỷ lệ (%)", "drop_vs_none": "Giảm so với none"}),
                     hide_index=True, use_container_width=True)
        st.markdown("**Theo mô hình (kèm tác vụ trượt)**")
        st.dataframe(df[["Cấu hình", "model", "done", "total", "rate", "failed_cases", "file"]]
                     .rename(columns={"model": "Mô hình", "done": "Đạt", "total": "Tổng",
                                      "rate": "Tỷ lệ (%)", "failed_cases": "Tác vụ trượt",
                                      "file": "Nguồn"}),
                     hide_index=True, use_container_width=True)
