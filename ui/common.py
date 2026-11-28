from html import escape

import streamlit as st
import config


def inject_custom_css():
    """Shared layout for the lab dashboard."""
    st.markdown(
        """
        <style>
        .stApp { background: #f1f4f9; }
        [data-testid="stHeader"] { background: transparent; }
        #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; }
        .stMainBlockContainer { max-width: 1220px; padding: 2.2rem 2.25rem 3rem; }
        [data-testid="stSidebar"] { background: #fff; border-right: 1px solid #dbe4ef; }

        .hero-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 14px;
            background: linear-gradient(112deg, #162641, #243a57 68%, #22555a);
            border: 1px solid #243650;
            border-radius: 16px;
            padding: 23px 27px;
            margin-bottom: 9px;
            box-shadow: 0 7px 18px #182b4a1e;
        }
        .hero-card .hero-title {
            color: #f7faff;
            font-size: clamp(1.55rem, 3vw, 2.18rem);
            font-weight: 720;
            letter-spacing: -0.035em;
            margin: 0;
            padding: 0;
        }
        .hero-card .hero-sub { color: #dbe6f7; font-size: 0.9rem; margin: 6px 0 0; }
        .pill-group { display: flex; gap: 7px; flex-wrap: wrap; }
        .pill { border-radius: 999px; padding: 5px 11px; font-size: 0.79rem; font-weight: 600; }
        .pill-blue { background: #e5eeff; color: #233e83; }
        .pill-green { background: #ddf5ed; color: #176252; }
        .pill-red { background: #fce7ec; color: #9d3050; }
        .pill-gray { background: #edf1f7; color: #334564; }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 4px;
            background: #e6ecf6;
            border: 1px solid #dbe3f1;
            border-radius: 11px;
            padding: 4px;
            margin-bottom: 8px;
        }
        [data-testid="stTabs"] [role="tab"] {
            border: 0;
            border-radius: 7px;
            color: #40516b;
            padding: 7px 13px;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: #fff;
            color: #213a73;
            box-shadow: 0 1px 5px #1a2e4920;
        }
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

        .lab-section { border-left: 4px solid #168477; padding: 2px 0 2px 14px; margin: 0 0 7px; }
        .lab-section h2 {
            color: #1c304c;
            font-size: 1.48rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            padding: 0;
            margin: 0;
        }
        .lab-section p { color: #506079; font-size: 0.9rem; margin: 4px 0 0; }
        .lab-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(157px, 100%), 1fr));
            gap: 10px;
            margin: 0 0 4px;
        }
        .lab-metric, .ui-card, [data-testid="stChatMessage"] {
            border: 1px solid #dce5f1;
            border-radius: 12px;
            background: #fff;
        }
        .lab-metric { padding: 12px 15px; min-width: 0; }
        .lab-metric-label { display: block; font-weight: 650; color: #3e516e; font-size: 0.82rem; }
        .lab-metric strong { color: #203965; font-size: 1.55rem; line-height: 1.46; font-variant-numeric: tabular-nums; }
        .lab-metric small { display: block; color: #52637a; font-size: 0.77rem; line-height: 1.4; }
        .ui-card { padding: 17px 20px; }
        [data-testid="stChatMessage"] { padding: 12px 16px; }
        .st-key-audit_filters, .st-key-audit_chart, .st-key-audit_reasons,
        .st-key-audit_events, .st-key-matrix_action, .st-key-matrix_leak,
        .st-key-utility_chart, .st-key-utility_detail, [class*="st-key-hitl_request_"] {
            background: #fff;
            border-radius: 13px;
        }
        .st-key-audit_reasons [data-testid="stText"],
        [class*="st-key-hitl_request_"] [data-testid="stText"] {
            overflow-wrap: anywhere;
            white-space: pre-wrap;
        }
        .verdict-box { border-radius: 10px; padding: 12px 16px; margin-top: 10px; font-size: 0.89rem; }
        .verdict-safe { background: #e5f5ee; color: #145f4e; border: 1px solid #bfe5d5; }
        .verdict-warn { background: #fff3de; color: #824707; border: 1px solid #f1d39e; }
        .verdict-leak { background: #fce9ed; color: #a22f4c; border: 1px solid #f3bbca; }
        .stButton > button { border-radius: 8px; font-weight: 600; }
        @media (max-width: 640px) {
            .stMainBlockContainer { padding-inline: 1rem; }
            .hero-card { padding: 19px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title, description):
    st.markdown(
        f'<header class="lab-section"><h2>{escape(title)}</h2><p>{escape(description)}</p></header>',
        unsafe_allow_html=True,
    )


def metric_cards(metrics):
    cards = "".join(
        f'<div class="lab-metric"><span class="lab-metric-label">{escape(str(label))}</span>'
        f'<strong>{escape(str(value))}</strong><small>{escape(str(detail))}</small></div>'
        for label, value, detail in metrics
    )
    st.markdown(f'<div class="lab-metrics">{cards}</div>', unsafe_allow_html=True)


def build_policy(layers):
    """layers: tap con cua {L1,L2,L3,L4}. Tra policy cho core.run_agent (None neu khong bat L2-L4)."""
    if not (layers & {"L2", "L3", "L4"}):
        return None
    from guardrails.policy import make_policy
    return make_policy(
        layer2="L2" in layers,
        layer3="L3" in layers,
        layer4="L4" in layers,
    )


def _set_all_layers(state: bool):
    for k in ("L1", "L2", "L3", "L4"):
        st.session_state[k] = state


def sidebar():
    with st.sidebar:
        st.markdown("### Điều khiển hệ thống")
        st.caption("Thiết lập mô hình và các lớp Guardrails thời gian thực.")

        model = st.selectbox(
            "Mô hình ngôn ngữ (LLM)",
            ["qwen2.5:3b", "llama3.2:3b", "dolphin-llama3:8b"],
            help="qwen2.5:3b = mục tiêu chính | llama3.2:3b = dễ bị thao túng | dolphin-llama3:8b = không kiểm duyệt",
        )

        st.divider()
        st.markdown("**Kiến trúc phòng thủ (4 lớp)**")

        p1, p2 = st.columns(2)
        with p1:
            st.button("Tắt hết", width="stretch", on_click=_set_all_layers, args=(False,))
        with p2:
            st.button("Bật đủ 4 lớp", width="stretch", on_click=_set_all_layers, args=(True,))

        c1 = st.toggle("Lớp 1 · Lọc HTML ẩn & Spotlighting", key="L1")
        c2 = st.toggle("Lớp 2 · Allowlist & Taint DB", key="L2")
        c3 = st.toggle("Lớp 3 · Quét rò rỉ đầu ra (DLP)", key="L3")
        c4 = st.toggle("Lớp 4 · Con người duyệt (HITL)", key="L4")

        layers = {name for on, name in [(c1, "L1"), (c2, "L2"), (c3, "L3"), (c4, "L4")] if on}
        config.ENABLE_L1 = "L1" in layers

        if layers:
            st.success(f"Đang kích hoạt: {', '.join(sorted(layers))}")
        else:
            st.warning("Chế độ mở: Không phòng thủ (none)")

        st.divider()
        st.markdown("**Môi trường Lab**")
        if st.button("Reset Lab (Xóa Mail & Tạo lại DB)", width="stretch"):
            from lab import reset_lab
            reset_lab.reset()
            for k in ("home_chat", "pending", "attack_steps"):
                st.session_state.pop(k, None)
            st.toast("Đã làm sạch 2 hộp thư và khởi tạo lại company.db", icon="✅")

    return {"model": model, "layers": layers, "policy": build_policy(layers)}
