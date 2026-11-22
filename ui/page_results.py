import streamlit as st


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">Bảng kết quả</div>
            <div style="color:#6E6E73; font-size:0.88rem;">
                Phần 5 sẽ xây: ma trận ASR theo lớp + biểu đồ + utility drop.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )