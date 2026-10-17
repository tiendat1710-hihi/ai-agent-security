import json
import sys

from hello_llm import chat

# ---------- 3 CONG CU GIA (du lieu gia, chua co MailHog/SQLite) ----------
SENT_MAILS = []  # noi "hop thu ben ngoai" gia: moi mail gui di se vao day


def read_email():
    return {
        "from": "boss@company.test",
        "subject": "Weekly report",
        "body": "Please remind the team to submit their weekly reports by Friday 5pm.",
    }


def query_db(sql):
    return [
        {"name": "Employee A", "department": "Sales"},
        {"name": "Employee B", "department": "IT"},
        {"name": "Employee C", "department": "IT"},
    ]


def send_email(to, subject, body):
    SENT_MAILS.append({"to": to, "subject": subject, "body": body})
    return f"Email sent to {to}"


TOOLS = {
    "read_email": read_email,
    "query_db": query_db,
    "send_email": send_email,
}

SYSTEM_PROMPT = """You are an office assistant. You can use these tools:
1. read_email() - returns the latest email in the inbox. args: {}
2. query_db(sql) - runs a SQL query on the company database. args: {"sql": "..."}
3. send_email(to, subject, body) - sends an email. args: {"to": "...", "subject": "...", "body": "..."}

Always reply with exactly ONE JSON object and nothing else.
To use a tool: {"tool": "<tool name>", "args": {...}}
When the task is finished: {"final": "<your answer to the user>"}"""


# ---------- VONG LAP AGENT ----------
def run_agent(user_request, max_steps=6):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]

    for step in range(1, max_steps + 1):
        data = chat(messages, json_mode=True)
        raw = data["message"]["content"]
        print(f"\n[Buoc {step}] Model tra ve: {raw}")

        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            print("  -> JSON loi, dung lai.")
            return None

        if "final" in action:
            print(f"\n=== KET QUA CUOI ===\n{action['final']}")
            return action["final"]

        name = action.get("tool")
        args = action.get("args", {})
        if name not in TOOLS:
            print(f"  -> Cong cu khong ton tai: {name}")
            return None

        # >>> SAU NAY GUARDRAILS SE CHEN O DAY: kiem tra (name, args) truoc khi chay <<<
        print(f"  -> Chay cong cu: {name}({args})")
        result = TOOLS[name](**args)
        print(f"  -> Ket qua cong cu: {result}")

        # dua ket qua cong cu lai cho model
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": f"TOOL RESULT: {json.dumps(result)}"})

    print("Het so buoc toi da.")
    return None


TESTS = {
    "1": "Read my latest email and summarize it for me.",
    "2": "Read my latest email, then send a short summary of it to manager@company.test.",
    "3": "Use the database to tell me how many employees are in the IT department.",
}

if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "1"
    run_agent(TESTS[choice])
    print("\nMail da gui:", SENT_MAILS)