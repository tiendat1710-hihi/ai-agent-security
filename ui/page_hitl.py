import streamlit as st


def render(ctx):
    st.markdown(
        """
        <div class="ui-card">
            <div style="font-weight:600; font-size:1.02rem; margin-bottom:4px;">Hàng đợi duyệt (HITL / Lớp 4)</div>
            <div style="color:#6E6E73; font-size:0.88rem;">
                Phần 3 sẽ xây: email bị treo PENDING_APPROVAL + nút Duyệt / Từ chối thật.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )