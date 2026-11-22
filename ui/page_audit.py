import streamlit as st


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">Nhật ký kiểm toán</div>
            <div style="color:#6E6E73; font-size:0.88rem;">
                Phần 4 sẽ xây: đọc log JSONL, lọc theo lớp/quyết định + thống kê.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )