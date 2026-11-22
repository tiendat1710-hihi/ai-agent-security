import streamlit as st
import config


def inject_custom_css():
    """CSS phong cach toi gian hien dai (Apple / Linear aesthetic)."""
    st.markdown(
        """
        <style>
        /* Font va nen tong the */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", sans-serif;
            color: #1D1D1F;
        }
        .stApp {
            background-color: #F5F5F7;
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        #MainMenu, footer, [data-testid="stDecoration"] {
            visibility: hidden;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 1220px;
        }

        /* Sidebar sang gon */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid rgba(0, 0, 0, 0.07);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.5rem;
        }

        /* Hero Header */
        .hero-card {
            background: #FFFFFF;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 18px;
            padding: 22px 28px;
            margin-bottom: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 14px;
        }
        .hero-title {
            font-size: 1.55rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            color: #1D1D1F;
            margin: 0;
        }
        .hero-sub {
            font-size: 0.92rem;
            color: #6E6E73;
            margin: 4px 0 0 0;
        }

        /* Pill Badges */
        .pill-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: -0.01em;
        }
        .pill-blue {
            background: #E8F2FF;
            color: #0066CC;
            border: 1px solid #C2DFFF;
        }
        .pill-green {
            background: #E8F8EE;
            color: #137333;
            border: 1px solid #B7E4C7;
        }
        .pill-red {
            background: #FCE8E6;
            color: #C5221F;
            border: 1px solid #F6AEA9;
        }
        .pill-gray {
            background: #F2F2F7;
            color: #3A3A3C;
            border: 1px solid #E5E5EA;
        }

        /* Tabs kieu thanh dieu huong hien dai */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: #E9E9EE;
            padding: 5px;
            border-radius: 12px;
            margin-bottom: 16px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 9px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 0.9rem;
            color: #515154;
            border: none;
            background: transparent;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #1D1D1F !important;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {
            display: none;
        }

        /* Card noi dung & Chat */
        .ui-card {
            background: #FFFFFF;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 16px;
            padding: 20px 24px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.025);
            margin-bottom: 14px;
        }
        [data-testid="stChatMessage"] {
            background-color: #FFFFFF;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 16px;
            padding: 14px 18px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
            margin-bottom: 10px;
        }

        /* Verdict banners */
        .verdict-box {
            border-radius: 12px;
            padding: 12px 16px;
            margin-top: 10px;
            font-size: 0.88rem;
            font-weight: 500;
        }
        .verdict-safe {
            background: #E8F8EE;
            color: #137333;
            border: 1px solid #B7E4C7;
        }
        .verdict-warn {
            background: #FEF7E0;
            color: #9A5500;
            border: 1px solid #FDE293;
        }
        .verdict-leak {
            background: #FCE8E6;
            color: #C5221F;
            border: 1px solid #F6AEA9;
        }

        /* Nut bam bo tron */
        .stButton > button {
            border-radius: 10px;
            font-weight: 500;
            border: 1px solid rgba(0, 0, 0, 0.1);
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            border-color: #0071E3;
            color: #0071E3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            st.button("Tắt hết", use_container_width=True, on_click=_set_all_layers, args=(False,))
        with p2:
            st.button("Bật đủ 4 lớp", use_container_width=True, on_click=_set_all_layers, args=(True,))

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
        if st.button("Reset Lab (Xóa Mail & Tạo lại DB)", use_container_width=True):
            from lab import reset_lab
            reset_lab.reset()
            for k in ("home_chat", "pending", "attack_steps"):
                st.session_state.pop(k, None)
            st.toast("Đã làm sạch 2 hộp thư và khởi tạo lại company.db", icon="✅")

    return {"model": model, "layers": layers, "policy": build_policy(layers)}