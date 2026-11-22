import streamlit as st


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">Tấn công trực tiếp</div>
            <div style="color:#6E6E73; font-size:0.88rem;">
                Phần 2 sẽ xây: chọn payload → nạp mail → chạy agent realtime (Plan → Act → Observe) → verdict trọng tài.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )