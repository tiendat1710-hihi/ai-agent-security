import os
import sys
from html import escape

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from ui.common import inject_custom_css, sidebar
from ui import page_attack, page_audit, page_hitl, page_home, page_results

st.set_page_config(
    page_title="AI Agent Security Lab",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()
ctx = sidebar()

active_layers = sorted(ctx["layers"])
if len(active_layers) == 4:
    posture_pill = '<span class="pill pill-green">Defense-in-Depth: L1 · L2 · L3 · L4</span>'
elif active_layers:
    posture_pill = f'<span class="pill pill-blue">Guardrails: {" · ".join(active_layers)}</span>'
else:
    posture_pill = '<span class="pill pill-red">Không phòng thủ (NONE)</span>'

st.markdown(
    f"""
    <div class="hero-card">
        <div>
            <h1 class="hero-title">AI Agent Security Lab</h1>
            <p class="hero-sub">Thử nghiệm prompt injection gián tiếp và phòng thủ đa lớp trên agent email.</p>
        </div>
        <div class="pill-group">
            <span class="pill pill-gray">{escape(ctx["model"])}</span>
            {posture_pill}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

t1, t2, t3, t4, t5 = st.tabs([
    "Thử nhanh",
    "Tấn công trực tiếp",
    "Hàng đợi duyệt (HITL)",
    "Nhật ký kiểm toán",
    "Bảng kết quả",
])
with t1:
    page_home.render(ctx)
with t2:
    page_attack.render(ctx)
with t3:
    page_hitl.render(ctx)
with t4:
    page_audit.render(ctx)
with t5:
    page_results.render(ctx)
