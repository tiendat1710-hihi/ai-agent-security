import re

import altair as alt
import pandas as pd
import streamlit as st

from experiments import build_matrix
from ui.common import metric_cards, section_header

CONFIG_LABELS = {
    "none": "Không phòng thủ",
    "all": "Đủ 4 lớp",
    "hitlok-all": "Đủ 4 lớp + duyệt",
}
MODEL_COLORS = ["#3857b6", "#087a65", "#a75a14", "#7652a8"]
TECHNIQUES = {
    "direct_override": "Ghi đè chỉ dẫn",
    "impersonation": "Giả danh",
    "urgency": "Tạo khẩn cấp",
    "hidden_instruction": "Chỉ dẫn ẩn",
    "fake_system_format": "Giả định dạng hệ thống",
    "split_instruction": "Chia nhỏ chỉ dẫn",
}


def config_label(name):
    return CONFIG_LABELS.get(name, name)


def read_csv(path, required):
    try:
        table = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError):
        st.warning(f"Không đọc được tệp {path.name}.")
        return None
    if not required.issubset(table.columns):
        st.warning(f"Tệp {path.name} thiếu cột cần thiết.")
        return None
    return table


def render(ctx):
    section_header("Bảng kết quả", "Đối chiếu hiệu quả phòng thủ và khả năng hoàn thành tác vụ hợp lệ.")
    st.caption("Dữ liệu lấy từ CSV đã lưu. Các tệp lịch sử có thể dùng cách chấm và cách tính ASR cũ.")
    asr_action, asr_leak, utility = st.tabs(["ASR-ACTION", "ASR-LEAK", "Utility"])
    with asr_action:
        _render_matrix("action", "Tỷ lệ lượt có thư xuất hiện trong hộp thư ngoài.")
    with asr_leak:
        _render_matrix("leak", "Tỷ lệ lượt hộp thư ngoài chứa dấu vết dữ liệu nhạy cảm.")
    with utility:
        _render_utility()


def _render_matrix(kind, description):
    section, filter_col = st.columns((2, 1))
    section.caption(description)
    path = build_matrix.RAW / f"matrix_asr_{kind}.csv"
    if not path.is_file():
        st.info("Chưa có ma trận. Chạy `python -m experiments.build_matrix` khi đã có kết quả ASR.")
        return
    source = read_csv(path, {"model", "ky_thuat"})
    if source is None:
        return
    columns = [name for name in source.columns if name not in {"model", "ky_thuat"}]
    models = sorted(source["model"].dropna().unique())
    if not columns or not models:
        st.info("Tệp ma trận chưa có kết quả.")
        return
    model = filter_col.selectbox("Mô hình", models, key=f"asr_model_{kind}")
    data = source[source["model"].eq(model)].drop(columns="model").rename(columns={"ky_thuat": "Kỹ thuật"})
    data["Kỹ thuật"] = data["Kỹ thuật"].replace(TECHNIQUES)
    for column in columns:
        numeric = pd.to_numeric(data[column], errors="coerce")
        data[column] = numeric.where(numeric.between(0, 100))
    long = data.melt("Kỹ thuật", var_name="Cấu hình", value_name="Tỷ lệ")
    long["Hiển thị"] = long["Tỷ lệ"].map(lambda v: "—" if pd.isna(v) else f"{v:g}%")
    with st.container(border=True, key=f"matrix_{kind}"):
        st.markdown("#### Tỷ lệ theo kỹ thuật và cấu hình")
        base = alt.Chart(long).encode(
            x=alt.X("Cấu hình:N", sort=columns, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Kỹ thuật:N", sort=data["Kỹ thuật"].tolist(), title=None),
        )
        cells = base.mark_rect(cornerRadius=4, stroke="white", strokeWidth=2).encode(
            color=alt.condition("isValid(datum['Tỷ lệ'])",
                                alt.Color("Tỷ lệ:Q", scale=alt.Scale(domain=[0, 100],
                                          range=["#eaf4f1", "#2b477f"]), legend=None),
                                alt.value("#f1f3f7")),
            tooltip=["Kỹ thuật:N", "Cấu hình:N", "Hiển thị:N"],
        )
        text = base.mark_text(fontSize=12, fontWeight=600).encode(
            text="Hiển thị:N",
            color=alt.condition("datum['Tỷ lệ'] >= 55", alt.value("white"), alt.value("#233650")),
        )
        st.altair_chart((cells + text).properties(height=max(150, 41 * len(data))), width="stretch")
        st.caption(f"—  Chưa có tỷ lệ · Nguồn {path.name}")
    with st.expander("Xem bảng số liệu"):
        st.dataframe(data, hide_index=True, width="stretch")


def _utility_rows():
    latest = {}
    for path in build_matrix.RAW.glob("utility_*_t*.csv"):
        match = re.fullmatch(r"utility_(.+)_t([^_]+)_(\d{8}_\d{4}(?:\d{2})?)", path.stem)
        if match is None:
            continue
        defense, temperature, run_date = match.groups()
        if defense not in latest or run_date > latest[defense][0]:
            latest[defense] = (run_date, temperature, path)
    groups = []
    for defense, (_, temperature, path) in latest.items():
        raw = read_csv(path, {"model", "case", "rep", "success"})
        if raw is None:
            continue
        valid = raw["success"].isin({"0", "1"}) & raw[["model", "case", "rep"]].notna().all(axis=1)
        if "error" in raw:
            valid &= raw["error"].isna() | raw["error"].eq("")
        observed = raw.loc[valid].drop_duplicates(["model", "case", "rep"])
        if not len(observed):
            st.warning(f"{path.name} không có lượt hợp lệ.")
            continue
        groups.append((defense, path, observed, len(raw) - len(observed), "status" not in raw, temperature))
    return groups


def _render_utility():
    groups = _utility_rows()
    if not groups:
        st.info("Chưa có kết quả Utility. Chạy `python -m experiments.bench_baseline` để tạo CSV.")
        return
    ordered = sorted(groups, key=lambda group: (list(CONFIG_LABELS).index(group[0])
                                                 if group[0] in CONFIG_LABELS else len(CONFIG_LABELS),
                                                 group[0]))
    labels = [config_label(defense) for defense, *_ in ordered]
    models = sorted({model for _, _, data, *_ in ordered for model in data["model"]})
    selected = st.multiselect("Mô hình", models, placeholder="Tất cả mô hình", key="utility_models")
    cards, results, sources, baseline = [], [], [], None
    for defense, path, data, excluded, historical, temperature in ordered:
        sources.append({"Cấu hình": config_label(defense), "Tệp CSV": path.name,
                        "Lượt không tính": excluded, "Bộ chấm": "Lịch sử" if historical else "Hiện tại",
                        "Temperature": temperature})
        if selected:
            data = data[data["model"].isin(selected)]
        if data.empty:
            continue
        succeeded = data["success"].eq("1").sum()
        rate = succeeded / len(data)
        cohort = set(data[["model", "case", "rep"]].itertuples(index=False, name=None))
        protocol = (cohort, historical, temperature)
        detail = f"{succeeded}/{len(data)} lượt hợp lệ hoàn thành"
        if defense == "none":
            baseline = (rate, protocol)
        elif baseline and baseline[1] == protocol:
            delta = (rate - baseline[0]) * 100
            detail += f" · {delta:+.1f} điểm % so với none"
        cards.append((config_label(defense), f"{rate:.1%}", detail))
        for model, rows in data.groupby("model"):
            failed = rows.loc[rows["success"].eq("0"), "case"]
            results.append({
                "Cấu hình": config_label(defense), "Mô hình": model,
                "Đạt": len(rows) - len(failed), "Tổng": len(rows),
                "Tỷ lệ (%)": round(100 * (len(rows) - len(failed)) / len(rows), 1),
                "Tác vụ trượt": ", ".join(sorted(failed.unique())) or "—",
            })
    if not results:
        st.info("Không có kết quả cho mô hình đã chọn.")
        return
    metric_cards(cards[:4])
    chart_data = pd.DataFrame(results)
    with st.container(border=True, key="utility_chart"):
        st.markdown("#### Tỷ lệ hoàn thành theo cấu hình")
        base = alt.Chart(chart_data).encode(
            x=alt.X("Cấu hình:N", sort=labels, title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="Mô hình:N",
            y=alt.Y("Tỷ lệ (%):Q", scale=alt.Scale(domain=[0, 110]),
                    axis=alt.Axis(values=[0, 25, 50, 75, 100]), title="% hoàn thành"),
        )
        bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            color=alt.Color("Mô hình:N", scale=alt.Scale(range=MODEL_COLORS), legend=alt.Legend(orient="top")),
            tooltip=["Cấu hình:N", "Mô hình:N", "Đạt:Q", "Tổng:Q", "Tỷ lệ (%):Q"],
        )
        labels_chart = base.mark_text(dy=-9, color="#334462", fontSize=11).encode(text="Tỷ lệ (%):Q")
        st.altair_chart((bars + labels_chart).properties(height=242), width="stretch")
    with st.container(border=True, key="utility_detail"):
        st.markdown("#### Chi tiết theo mô hình")
        st.dataframe(chart_data, hide_index=True, width="stretch")
    with st.expander("Nguồn số liệu"):
        st.caption("Tỷ lệ dùng số lượt hợp lệ trong từng tệp. Kiểm tra bộ ca và cách chấm trước khi so sánh.")
        st.dataframe(pd.DataFrame(sources), hide_index=True, width="stretch")
