import sys
import json
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
        st.subheader("Nhat ky Tool Call")
        log_files = sorted(config.LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            st.info("Chua co lan chay nao. Vao tab Chat de bat dau.")
        else:
            chosen = st.selectbox("Chon lan chay (moi nhat o tren)",
                                  log_files, format_func=lambda p: p.stem)
            rows = [json.loads(l) for l in chosen.read_text(encoding="utf-8").splitlines()]
            for r in rows:
                icon = {"tool_call": "->", "tool_result": "<-", "final_answer": "OK",
                        "guardrail_decision": "!!", "user_request": ">>"}.get(r["event"], "-")
                st.text(f"{icon} [{r['event']}] tool={r.get('tool')} decision={r.get('decision')} "
                        f"| {r.get('result_preview') or r.get('reason') or ''}")

with tab_compare:
        st.subheader("Baseline: Ty le hoan thanh tac vu hop le (tuan 3)")
        baseline_files = sorted((config.ROOT / "experiments" / "results_raw").glob("baseline_*.csv"))
        if baseline_files:
            import pandas as pd
            df = pd.read_csv(baseline_files[-1])
            summary = df[df["error"].isna()].groupby("model")["success"].agg(["sum", "count"])
            # Đã thêm dấu * vào phép nhân 100 để không bị lỗi cú pháp
            summary["ty_le"] = (summary["sum"] / summary["count"] * 100).round(1).astype(str) + "%"
            st.dataframe(summary.rename(columns={"sum": "Dat", "count": "Tong"}))
        else:
            st.info("Chua co file baseline. Chay experiments/bench_baseline.py truoc.")
            
        st.divider()
        st.subheader("Doi chieu: hop thu NOI BO vs BEN NGOAI")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Hop thu NOI BO**")
            for m in mail_client.list_messages(config.INTERNAL_MAIL)[:10]:
                st.text(f"{m['from']} -> {m['to']} | {m['subject']}")
        with col2:
            st.markdown("**Hop thu BEN NGOAI (hacker)**")
            external = mail_client.list_messages(config.EXTERNAL_MAIL)[:10]
            if external:
                st.error(f"{len(external)} thu da lot ra ngoai!")
            for m in external:
                st.text(f"{m['from']} -> {m['to']} | {m['subject']}")
        st.caption("Canh bao do va nut Duyet/Tu choi se them o tuan 7")