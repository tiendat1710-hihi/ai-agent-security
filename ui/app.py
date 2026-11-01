import sys
import os
# Thêm thư mục gốc (D:\ai-agent-security) vào sys.path để Python tìm thấy config, agent, v.v.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import streamlit as st
import config
from agent import core
from experiments.logger import RunLogger, read_run
from lab import leak_checker, mail_client

st.set_page_config(page_title="AI Agent Security Lab", layout="wide")
st.title("AI Agent Security Lab — Demo")

if "chat" not in st.session_state:
    st.session_state.chat = []       # [(role, text), ...]
if "last_run_id" not in st.session_state:
    st.session_state.last_run_id = None

with st.sidebar:
    st.header("Cau hinh")
    model = st.selectbox("Mo hinh", ["dolphin-llama3:8b", "llama3.2:3b", "qwen2.5:3b"])
    guardrails_on = st.toggle("Guardrails", value=False,
                              help="Chua co tac dung o tuan 2, se noi that o tuan 6-7")
    if st.button("Reset lab (xoa 2 hop thu, sinh lai du lieu)"):
        from lab import reset_lab
        reset_lab.reset()
        st.session_state.chat = []
        st.success("Da reset lab.")

tab_chat, tab_log, tab_compare = st.tabs(
    ["💬 Chatbot", "🧾 Nhat ky tool call", "⚔️ Tan cong vs Phong thu"])

with tab_chat:
    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.write(text)

    prompt = st.chat_input("Nhap yeu cau cho tro ly...")
    if prompt:
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.write(prompt)

        log = RunLogger(model)
        with st.spinner(f"{model} dang xu ly..."):
            # policy=None hien tai: moi hanh dong deu ALLOW (tuan 6-7 se gan Guardrails that)
            res = core.run_agent(prompt, model=model, policy=None, emit=log.emit)

        answer = res["final"] or "(khong co cau tra loi, co the da het so buoc)"
        st.session_state.chat.append(("assistant", answer))
        st.session_state.last_run_id = log.run_id
        with st.chat_message("assistant"):
            st.write(answer)
            if res["tool_calls"]:
                st.caption("Cong cu da goi: " + " -> ".join(c["tool"] for c in res["tool_calls"]))

with tab_log:
    st.subheader("Nhat ky lan chay gan nhat")
    if st.session_state.last_run_id:
        rows = read_run(st.session_state.last_run_id)
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Chua co lan chay nao. Hay chat o tab ben trai.")

with tab_compare:
    st.subheader("Tinh trang hop thu (du lieu that tu lab)")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("So thu hop thu NOI BO", len(mail_client.list_messages(config.INTERNAL_MAIL)))
    with c2:
        ext = leak_checker.check_external()
        st.metric("So thu hop thu BEN NGOAI (hacker)", ext["messages"])
        if ext["leaked"]:
            st.error(f"⚠️ PHAT HIEN RO RI: {ext['leaked_mails']} thu chua du lieu mat "
                     f"({ext['distinct_markers']} marker)")
        else:
            st.success("Chua phat hien ro ri du lieu mat.")
    st.caption("Man hinh nay se duoc nang cap thanh 2 cot Tan cong / Phong thu that o tuan 7-9.")